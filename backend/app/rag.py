# ==============================================================================
# RAG Pipeline: In-Process ChromaDB Retrieval Engine with Standalone ONNX Embeddings
# ==============================================================================
# Responsibilities:
#   1. Parses Markdown documents from /app/data into semantic chunks.
#   2. Generates vector embeddings directly in-process via ONNX (all-MiniLM-L6-v2)
#      with zero dependencies on external APIs or running Ollama containers.
#   3. Stores vectors in an in-process persistent ChromaDB database.
#   4. Performs cosine similarity queries against incoming user prompts.
#   5. Synthesizes a factual, grounded system prompt for the LLM.
# ==============================================================================

import glob
import logging
import os
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Metadata
from chromadb.utils import embedding_functions

logger = logging.getLogger("chatbot-rag")


class RAGPipeline:
    """
    Manages in-process ChromaDB vector store, document ingestion,
    and contextual semantic search for the portfolio chatbot.
    """

    def __init__(
        self,
        persist_dir: str = "/app/chroma_db",
        data_dir: str = "/app/data",
        collection_name: str = "portfolio_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_function: Any = None,
        ollama_host: str | None = None,
        **kwargs: Any,
    ):
        self.persist_dir = persist_dir
        self.data_dir = data_dir
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.client: ClientAPI | None = None
        self.collection: Collection | None = None
        self.embedding_fn: Any = embedding_function

    def get_collection(self) -> Collection:
        """
        Safely retrieve or refresh the collection handle from ChromaDB.
        Guarantees self-healing against stale handles if the database was
        modified or refreshed externally.
        """
        if self.client is None:
            self.client = chromadb.PersistentClient(path=self.persist_dir)

        if self.embedding_fn is None:
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        try:
            if self.collection is not None:
                # Validate handle against ChromaDB engine
                _ = self.collection.count()
                return self.collection
        except Exception:  # noqa: BLE001
            logger.warning("Cached collection handle is stale or invalid; re-acquiring...")

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "Haniff Kamal Portfolio Knowledge Base"},
        )
        return self.collection

    def initialize(self):
        """Initialize ChromaDB client and ingest knowledge base documents."""
        os.makedirs(self.persist_dir, exist_ok=True)
        logger.info("Initializing ChromaDB persistent client at %s", self.persist_dir)

        # In-process ONNX embeddings (all-MiniLM-L6-v2)
        # 100% self-contained: works regardless of Ollama status and runs fast on CPU
        if self.embedding_fn is None:
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # In-process persistent ChromaDB instance
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        try:
            self.collection = self.get_collection()
        except ValueError as exc:
            if "conflict" in str(exc).lower() or "dimensionality" in str(exc).lower():
                logger.info(
                    "Resetting collection due to embedding model upgrade: %s", exc
                )
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_fn,
                    metadata={"description": "Haniff Kamal Portfolio Knowledge Base"},
                )
            else:
                raise

        # Ingest documents on startup
        self.ingest_markdown_files()

    def _chunk_markdown(self, filename: str, content: str) -> list[dict[str, Any]]:
        """
        Split markdown content into semantic chunks based on headers.
        Extracts top-level document title and prepends rich context headers
        to maximize vector similarity during RAG retrieval.
        """
        chunks: list[dict[str, Any]] = []
        base_name = os.path.basename(filename).replace(".md", "").capitalize()
        lines = content.split("\n")

        # Extract top-level document title if available
        doc_title = base_name
        for line in lines:
            if line.startswith("# ") and not line.startswith("## "):
                doc_title = line.lstrip("#").strip()
                break

        current_header = doc_title
        current_lines: list[str] = []

        for line in lines:
            if line.startswith(("## ", "### ")):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    # Strip leading level-1 header if present to avoid empty title chunks
                    if chunk_text.startswith(f"# {doc_title}"):
                        chunk_text = chunk_text[len(f"# {doc_title}") :].strip()

                    # Only register chunks with substantial content (ignore title-only blocks)
                    if len(chunk_text) > 30:
                        chunks.append(
                            {
                                "text": f"[{doc_title} - {current_header}]\n{chunk_text}",
                                "source": os.path.basename(filename),
                                "section": current_header,
                            }
                        )
                    current_lines = []
                current_header = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        # Append final chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text.startswith(f"# {doc_title}"):
                chunk_text = chunk_text[len(f"# {doc_title}") :].strip()

            if len(chunk_text) > 30:
                chunks.append(
                    {
                        "text": f"[{doc_title} - {current_header}]\n{chunk_text}",
                        "source": os.path.basename(filename),
                        "section": current_header,
                    }
                )

        return chunks

    def ingest_markdown_files(self):
        """Read all .md files from data directory, chunk them, and index into ChromaDB."""
        search_pattern = os.path.join(self.data_dir, "*.md")
        files = glob.glob(search_pattern)

        if not files:
            logger.warning("No markdown files found in %s to index.", self.data_dir)
            return

        collection = self.get_collection()
        logger.info("Ingesting %d markdown files from %s...", len(files), self.data_dir)

        # Clear existing records safely by ID to avoid invalidating the collection handle
        try:
            existing = collection.get()
            existing_ids = existing.get("ids", [])
            if existing_ids:
                logger.info(
                    "Clearing %d existing chunks before re-indexing...", len(existing_ids)
                )
                collection.delete(ids=existing_ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not clear existing chunks, will upsert: %s", exc)

        documents: list[str] = []
        metadatas: list[Metadata] = []
        ids: list[str] = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = self._chunk_markdown(file_path, content)
                base_name = os.path.basename(file_path).replace(".md", "")

                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{base_name}_{idx}"
                    documents.append(chunk["text"])
                    metadatas.append(
                        {"source": chunk["source"], "section": chunk["section"]}
                    )
                    ids.append(chunk_id)

            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to parse markdown file %s: %s", file_path, exc)

        if documents:
            collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(
                "Successfully indexed %d chunks across %d documents into ChromaDB.",
                len(documents),
                len(files),
            )

    def retrieve_context(self, query: str, n_results: int = 4) -> str:
        """
        Query ChromaDB for the most semantically relevant chunks matching user query.
        Returns a formatted string ready for LLM prompt augmentation.
        """
        try:
            collection = self.get_collection()
            count = collection.count()
            if count == 0:
                logger.warning("ChromaDB collection is empty.")
                return ""

            results = collection.query(
                query_texts=[query], n_results=min(n_results, count)
            )

            docs_list = results.get("documents")
            if not docs_list or not docs_list[0]:
                return ""

            retrieved_docs = docs_list[0]
            context_blocks: list[str] = []
            for doc in retrieved_docs:
                context_blocks.append(f"---\n{doc}")

            return "\n\n".join(context_blocks)

        except Exception as exc:  # noqa: BLE001
            logger.error("Error retrieving context from ChromaDB: %s", exc)
            return ""

    def build_system_prompt(self, context: str) -> str:
        """Construct a strict, grounded system prompt with retrieved context."""
        base_prompt = (
            "You are Haniff Kamal's official AI Portfolio Assistant.\n"
            "Your job is to provide accurate, concise, and professional answers to visitors, "
            "recruiters, and engineers asking about Haniff.\n\n"
            "STRICT GUIDELINES:\n"
            "1. Base your answer strictly on the verified portfolio facts provided below.\n"
            "2. If the user asks something not covered in the context, politely inform them that you only "
            "have information on Haniff's Computer Engineering background, Audio Deepfake Detection research, "
            "and DevOps/MLOps cloud projects.\n"
            "3. Format your answers cleanly using Markdown bullet points or Markdown tables.\n"
            "4. Strictly mirror the verified skills and tools listed in the context. Do NOT invent, assume, "
            "or extrapolate tools (e.g. do NOT mention Jenkins, CircleCI, Perl, or AWS Lambda unless present in the context).\n"
            "5. Keep responses factual, direct, and professional."
        )

        if context.strip():
            return f"{base_prompt}\n\n=== VERIFIED PORTFOLIO CONTEXT ===\n{context}\n================================="
        else:
            return base_prompt
