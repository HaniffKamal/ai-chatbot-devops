# ==============================================================================
# FastAPI Backend: Asynchronous LLM Inference & RAG Microservice
# ==============================================================================
# Responsibilities:
#   1. Exposes public REST endpoints (/api/chat, /health).
#   2. Validates user input payloads using strict Pydantic schemas.
#   3. Manages an in-process ChromaDB vector store for RAG grounding.
#   4. Maintains an asynchronous HTTP connection pool to Ollama (http://ollama:11434).
#   5. Handles upstream timeouts, connection failures, and error logging gracefully.
# ==============================================================================

import logging
import os
from contextlib import asynccontextmanager

import httpx
from app.rag import RAGPipeline
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# 1. Structured Application Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chatbot-backend")

# ------------------------------------------------------------------------------
# 2. Dynamic Environment Configuration
# ------------------------------------------------------------------------------
OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST", "http://ollama:11434"
)  # Internal Docker DNS for Ollama
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:1b")  # Default model to query
OLLAMA_TIMEOUT = float(
    os.getenv("OLLAMA_TIMEOUT", "60.0")
)  # Maximum time (s) to wait for LLM
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_db")
KNOWLEDGE_DATA_DIR = os.getenv("KNOWLEDGE_DATA_DIR", "/app/data")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Global singletons
http_client: httpx.AsyncClient | None = None
rag_pipeline: RAGPipeline | None = None


# ------------------------------------------------------------------------------
# 3. Application Lifespan (Startup & Shutdown Event Manager)
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of HTTP client pool and in-process ChromaDB vector store."""
    global http_client, rag_pipeline
    logger.info("Initializing HTTP client connection pool to Ollama at %s", OLLAMA_HOST)

    # Initialize connection pool with timeouts
    http_client = httpx.AsyncClient(
        base_url=OLLAMA_HOST, timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=5.0)
    )

    # Initialize embedded ChromaDB RAG pipeline
    try:
        rag_pipeline = RAGPipeline(
            persist_dir=CHROMA_PERSIST_DIR,
            data_dir=KNOWLEDGE_DATA_DIR,
            ollama_host=OLLAMA_HOST,
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        )
        rag_pipeline.initialize()
        logger.info("RAG pipeline successfully initialized.")
    except Exception:
        logger.exception("Failed to initialize RAG pipeline")

    yield

    # Clean shutdown
    logger.info("Closing HTTP client connection pool...")
    if http_client:
        await http_client.aclose()


# ------------------------------------------------------------------------------
# 4. FastAPI Application Initialization
# ------------------------------------------------------------------------------
app = FastAPI(title="AI Portfolio Chatbot API", version="1.0.0", lifespan=lifespan)

# ------------------------------------------------------------------------------
# 5. Cross-Origin Resource Sharing (CORS) Configuration
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
        description="User message content (capped at 1000 chars to prevent prompt injection / abuse)",
    )
    model: str | None = Field(
        default=None,
        description="Optional target model name; falls back to DEFAULT_MODEL if omitted",
    )


class ChatResponse(BaseModel):
    """Schema for successful chatbot reply sent back to the frontend."""

    reply: str
    model: str
    context_used: bool = False
    status: str = "success"


class HealthResponse(BaseModel):
    """Schema for the healthcheck verification endpoint."""

    status: str
    ollama_connected: bool
    configured_model: str
    rag_indexed_chunks: int = 0


# ------------------------------------------------------------------------------
# 7. Healthcheck Route: GET /health
# ------------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify backend health, Ollama connectivity, and ChromaDB chunk count."""
    ollama_ok = False

    if http_client:
        try:
            response = await http_client.get("/api/tags", timeout=3.0)
            ollama_ok = response.status_code == status.HTTP_200_OK
        except Exception as exc:  # noqa: BLE001
            logger.warning("Health check failed to reach Ollama: %s", exc)

    rag_chunks = 0
    if rag_pipeline and rag_pipeline.collection:
        try:
            rag_chunks = rag_pipeline.collection.count()
        except Exception:  # noqa: BLE001
            rag_chunks = 0

    return HealthResponse(
        status="ok",
        ollama_connected=ollama_ok,
        configured_model=DEFAULT_MODEL,
        rag_indexed_chunks=rag_chunks,
    )


# ------------------------------------------------------------------------------
# 8. Chat Generation Route: POST /api/chat
# ------------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Retrieves grounding context from ChromaDB, constructs a secured system prompt,
    and forwards inference asynchronously to Ollama.
    """
    if not http_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HTTP client pool is not initialized",
        )

    # 1. Semantic retrieval from ChromaDB knowledge base
    retrieved_context = ""
    system_prompt = ""
    if rag_pipeline:
        try:
            retrieved_context = rag_pipeline.retrieve_context(
                request.message, n_results=2
            )
            system_prompt = rag_pipeline.build_system_prompt(retrieved_context)
            logger.info(
                "RAG context retrieved (%d chars) for query: '%s'",
                len(retrieved_context),
                request.message[:60],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG retrieval failed, proceeding without context: %s", exc)
            system_prompt = rag_pipeline.build_system_prompt("")

    # 2. Prepare payload for Ollama
    model_to_use = request.model or DEFAULT_MODEL
    payload = {
        "model": model_to_use,
        "prompt": request.message,
        "system": system_prompt,
        "stream": False,
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
            reply=reply_text, model=model_to_use, context_used=bool(retrieved_context)
        )

    except httpx.ConnectError:
        logger.error("Failed to connect to Ollama at %s", OLLAMA_HOST)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference service unreachable. Ensure Ollama container is healthy.",
        )

    except httpx.TimeoutException:
        logger.error("Inference timed out after %s seconds", OLLAMA_TIMEOUT)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Inference request timed out after {OLLAMA_TIMEOUT}s.",
        )

    except Exception as exc:
        logger.exception("Error processing LLM request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal inference failure: {exc}",
        ) from exc
