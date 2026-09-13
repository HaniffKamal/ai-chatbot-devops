import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chatbot-backend")

# Configuration via environment variables
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))

# Global reusable async HTTP client
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of the shared HTTP client pool."""
    global http_client
    logger.info("Initializing HTTP client connection pool to Ollama at %s", OLLAMA_HOST)
    http_client = httpx.AsyncClient(
        base_url=OLLAMA_HOST,
        timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=5.0)
    )
    yield
    logger.info("Closing HTTP client connection pool...")
    await http_client.aclose()


app = FastAPI(
    title="AI Portfolio Chatbot API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to domain in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User message content"
    )
    model: Optional[str] = Field(
        default=None,
        description="Target model name, defaults to server configuration"
    )


class ChatResponse(BaseModel):
    reply: str
    model: str
    status: str = "success"


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    configured_model: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify backend health and active connectivity to the Ollama container."""
    global http_client
    ollama_ok = False

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

    model_to_use = request.model or DEFAULT_MODEL
    payload = {
        "model": model_to_use,
        "prompt": request.message,
        "stream": False
    }

    logger.info("Forwarding prompt to Ollama model '%s'", model_to_use)

    try:
        response = await http_client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        reply_text = data.get("response", "").strip()

        if not reply_text:
            raise ValueError("Ollama returned an empty response string")

        return ChatResponse(
            reply=reply_text,
            model=model_to_use
        )

    except httpx.ConnectError:
        logger.error("Failed to connect to Ollama at %s", OLLAMA_HOST)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference service unreachable. Ensure Ollama container is healthy."
        )

    except httpx.TimeoutException:
        logger.error("Inference timed out after %s seconds", OLLAMA_TIMEOUT)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Inference request timed out after {OLLAMA_TIMEOUT}s."
        )

    except Exception as exc:
        logger.error("Error processing LLM request: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal inference failure: {str(exc)}"
        )
