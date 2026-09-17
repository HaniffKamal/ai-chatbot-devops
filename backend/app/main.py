# ==============================================================================
# FastAPI Backend: Asynchronous LLM Inference & Orchestration Microservice
# ==============================================================================
# Responsibilities:
#   1. Exposes public REST endpoints (/api/chat, /health).
#   2. Validates user input payloads using strict Pydantic schemas.
#   3. Maintains an asynchronous HTTP connection pool to Ollama (http://ollama:11434).
#   4. Handles upstream timeouts, connection failures, and error logging gracefully.
# ==============================================================================

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# 1. Structured Application Logging
# ------------------------------------------------------------------------------
# Configures timestamped logging for container stdout/stderr.
# Docker logging drivers (json-file) read this directly for log aggregation.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chatbot-backend")

# ------------------------------------------------------------------------------
# 2. Dynamic Environment Configuration
# ------------------------------------------------------------------------------
# Reads settings from the .env file or environment variables injected by Docker.
# Fallback defaults are provided in case .env is missing.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")    # Internal Docker DNS for Ollama
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.1:8b")        # Default model to query
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))     # Maximum time (s) to wait for LLM

# Global reusable asynchronous HTTP client connection pool
http_client: Optional[httpx.AsyncClient] = None


# ------------------------------------------------------------------------------
# 3. Application Lifespan (Startup & Shutdown Event Manager)
# ------------------------------------------------------------------------------
# Modern FastAPI pattern replacing deprecated @app.on_event("startup") / "shutdown".
# Manages connection pooling: establishes one persistent TCP pool to Ollama on boot
# and gracefully terminates connections when the container stops.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of the shared HTTP client pool."""
    global http_client
    logger.info("Initializing HTTP client connection pool to Ollama at %s", OLLAMA_HOST)
    
    # Initialize the client pool with connection timeouts
    http_client = httpx.AsyncClient(
        base_url=OLLAMA_HOST,
        timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=5.0)
    )
    
    # 'yield' hands control over to FastAPI to start processing incoming HTTP requests
    yield
    
    # Code below 'yield' runs when the application shuts down (SIGTERM from Docker)
    logger.info("Closing HTTP client connection pool...")
    await http_client.aclose()


# ------------------------------------------------------------------------------
# 4. FastAPI Application Initialization
# ------------------------------------------------------------------------------
app = FastAPI(
    title="AI Portfolio Chatbot API",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------------------
# 5. Cross-Origin Resource Sharing (CORS) Configuration
# ------------------------------------------------------------------------------
# Controls which domains/browsers are allowed to make AJAX/fetch requests to this API.
# In local development, allow all origins ("*"). Restrict to haniffkamal.my in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# 6. Pydantic Request & Response Schemas (Input Validation)
# ------------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Schema for incoming user chat messages with boundary protection."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User message content (capped at 1000 chars to prevent prompt injection / abuse)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional target model name; falls back to DEFAULT_MODEL if omitted"
    )


class ChatResponse(BaseModel):
    """Schema for successful chatbot reply sent back to the frontend."""
    reply: str
    model: str
    status: str = "success"


class HealthResponse(BaseModel):
    """Schema for the healthcheck verification endpoint."""
    status: str
    ollama_connected: bool
    configured_model: str


# ------------------------------------------------------------------------------
# 7. Healthcheck Route: GET /health
# ------------------------------------------------------------------------------
# Used by Docker HEALTHCHECK, AWS Load Balancers, and Prometheus monitoring to verify
# that this microservice is alive and actively capable of communicating with Ollama.
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify backend health and active connectivity to the Ollama container."""
    global http_client
    ollama_ok = False

    # Ping Ollama's /api/tags endpoint to check if Ollama daemon is awake and responsive
    if http_client:
        try:
            response = await http_client.get("/api/tags", timeout=3.0)
            ollama_ok = response.status_code == status.HTTP_200_OK
        except Exception as exc:
            logger.warning("Health check failed to reach Ollama: %s", exc)

    return HealthResponse(
        status="ok",
        ollama_connected=ollama_ok,
        configured_model=DEFAULT_MODEL
    )


# ------------------------------------------------------------------------------
# 8. Chat Generation Route: POST /api/chat
# ------------------------------------------------------------------------------
# Core endpoint: receives user message, delegates inference to Ollama asynchronously,
# and returns the generated text answer to the frontend chat widget.
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Accepts user prompt and forwards it asynchronously to Ollama's generate API.
    """
    global http_client
    if not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HTTP client pool is not initialized"
        )

    # Use model specified in request, or fall back to system default (llama3.1:8b)
    model_to_use = request.model or DEFAULT_MODEL
    payload = {
        "model": model_to_use,
        "prompt": request.message,
        "stream": False                  # Non-streaming for clean JSON response
    }

    logger.info("Forwarding prompt to Ollama model '%s'", model_to_use)

    try:
        # Asynchronously send POST request to Ollama's /api/generate endpoint
        # 'await' ensures the thread is not blocked while the GPU computes the answer
        response = await http_client.post("/api/generate", json=payload)
        response.raise_for_status()       # Raises an HTTPStatusError if Ollama returned 4xx/5xx
        
        data = response.json()
        reply_text = data.get("response", "").strip()

        if not reply_text:
            raise ValueError("Ollama returned an empty response string")

        return ChatResponse(
            reply=reply_text,
            model=model_to_use
        )

    # Error Case 1: Ollama container is down, stopped, or restarting
    except httpx.ConnectError:
        logger.error("Failed to connect to Ollama at %s", OLLAMA_HOST)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference service unreachable. Ensure Ollama container is healthy."
        )

    # Error Case 2: Model took longer than OLLAMA_TIMEOUT (60s) to generate text
    except httpx.TimeoutException:
        logger.error("Inference timed out after %s seconds", OLLAMA_TIMEOUT)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Inference request timed out after {OLLAMA_TIMEOUT}s."
        )

    # Error Case 3: Any unexpected generic failure
    except Exception as exc:
        logger.error("Error processing LLM request: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal inference failure: {str(exc)}"
        )
