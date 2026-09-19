# ==============================================================================
# FastAPI Backend: Asynchronous Dual-Engine LLM Inference & RAG Microservice
# ==============================================================================
# Responsibilities:
#   1. Exposes public REST endpoints (/api/chat, /health).
#   2. Validates user input payloads using strict Pydantic schemas.
#   3. Manages an in-process ChromaDB vector store for RAG grounding.
#   4. Orchestrates Dual-Engine LLM inference (Ollama primary + Groq Cloud fallback).
#   5. Enforces graceful degradation without exposing unhandled 500 exceptions (Rule 4.1).
# ==============================================================================

import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.llm_client import DualEngineLLM
from app.rag import RAGPipeline
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# 1. Structured Application Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chatbot-backend")

# Global service singletons
dual_engine: DualEngineLLM | None = None
rag_pipeline: RAGPipeline | None = None


# ------------------------------------------------------------------------------
# 2. Application Lifespan (Startup & Shutdown Event Manager)
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage lifecycle of Dual-Engine LLM pool and in-process ChromaDB vector store."""
    global dual_engine, rag_pipeline
    logger.info(
        "Starting AI Chatbot Backend in '%s' environment...", settings.ENVIRONMENT
    )

    # 1. Initialize Dual-Engine LLM Connection Pools
    dual_engine = DualEngineLLM(app_settings=settings)
    dual_engine.initialize()

    # 2. Initialize embedded ChromaDB RAG pipeline
    try:
        rag_pipeline = RAGPipeline(
            persist_dir=settings.CHROMA_PERSIST_DIR,
            data_dir=settings.KNOWLEDGE_DATA_DIR,
            embedding_model=settings.EMBEDDING_MODEL,
        )
        rag_pipeline.initialize()
        logger.info("RAG pipeline successfully initialized.")
    except Exception:
        logger.exception("Failed to initialize RAG pipeline")

    yield

    # 3. Clean shutdown
    logger.info("Shutting down AI Chatbot Backend...")
    if dual_engine:
        await dual_engine.aclose()


# ------------------------------------------------------------------------------
# 3. FastAPI Application Initialization
# ------------------------------------------------------------------------------
app = FastAPI(
    title="AI Portfolio Chatbot API",
    version="1.1.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# 4. Cross-Origin Resource Sharing (CORS) Configuration
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# 5. Pydantic Request & Response Schemas (Input Validation)
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
    """Schema for chatbot reply sent back to the frontend."""

    reply: str
    model: str
    provider: str = "ollama"  # "ollama" | "groq" | "system-fallback"
    context_used: bool = False
    status: str = "success"  # "success" | "degraded"


class HealthResponse(BaseModel):
    """Schema for the healthcheck verification endpoint."""

    status: str
    ollama_connected: bool
    groq_configured: bool
    groq_connected: bool
    configured_model: str
    fallback_model: str
    rag_indexed_chunks: int = 0


# ------------------------------------------------------------------------------
# 6. Healthcheck Route: GET /health
# ------------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify backend health, Ollama status, Groq fallback status, and ChromaDB count."""
    ollama_ok = False
    groq_ok = False

    if dual_engine:
        ollama_ok = await dual_engine.check_ollama_health()
        groq_ok = await dual_engine.check_groq_health()

    rag_chunks = 0
    if rag_pipeline:
        try:
            rag_chunks = rag_pipeline.get_collection().count()
        except Exception:  # noqa: BLE001
            rag_chunks = 0

    return HealthResponse(
        status="ok",
        ollama_connected=ollama_ok,
        groq_configured=settings.is_groq_enabled,
        groq_connected=groq_ok,
        configured_model=settings.DEFAULT_MODEL,
        fallback_model=settings.GROQ_MODEL,
        rag_indexed_chunks=rag_chunks,
    )


# ------------------------------------------------------------------------------
# 7. Chat Generation Route: POST /api/chat
# ------------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Retrieves grounding context from ChromaDB, constructs a secured system prompt,
    and forwards inference to DualEngineLLM (Ollama primary -> Groq fallback).
    """
    if not dual_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dual-engine LLM client is not initialized",
        )

    # 1. Semantic retrieval from ChromaDB knowledge base
    retrieved_context = ""
    system_prompt = ""
    if rag_pipeline:
        try:
            retrieved_context = rag_pipeline.retrieve_context(
                request.message, n_results=5
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

    # 2. Forward inference through Dual-Engine LLM (Ollama -> Groq -> Graceful Fallback)
    result = await dual_engine.generate_response(
        prompt=request.message,
        system_prompt=system_prompt,
        model=request.model,
    )

    return ChatResponse(
        reply=result.text,
        model=result.model,
        provider=result.provider,
        context_used=bool(retrieved_context),
        status="success" if result.success else "degraded",
    )
