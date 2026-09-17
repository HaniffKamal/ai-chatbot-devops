# ==============================================================================
# RAG Pipeline: In-Process ChromaDB Retrieval Engine with Ollama Embeddings
# ==============================================================================
# Responsibilities:
#   1. Parses Markdown documents from /app/data into semantic chunks.
#   2. Delegates vector embeddings directly to local Ollama (nomic-embed-text)
#      using native GPU acceleration without external S3 download bottlenecks.
#   3. Stores vectors in an in-process ChromaDB database.
#   4. Performs cosine similarity queries against incoming user prompts.
#   5. Synthesizes a factual, grounded system prompt for the LLM.
# ==============================================================================

import os
import glob
import logging
from typing import List, Dict, Any, Optional

import httpx
import chromadb

logger = logging.getLogger("chatbot-rag")


class LocalOllamaEmbeddingFunction:
    """
    Zero-overhead embedding function connecting directly to local Ollama.
    Bypasses slow external S3 downloads and leverages your NVIDIA RTX 3060 GPU.
    """

    def __init__(self, host: str = "http://ollama:11434", model: str = "nomic-embed-text"):
        self.host = host.rstrip("/")
        self.model = model

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings = []
        with httpx.Client(base_url=self.host, timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            for text in input:
                try:
                    response = client.post("/api/embeddings", json={
                        "model": self.model,
                        "prompt": text
                    })
                    response.raise_for_status()
                    embeddings.append(response.json()["embedding"])
                except Exception as exc:
                    logger.error("Failed to generate embedding for text '%s...': %s", text[:40], exc)
                    raise
        return embeddings

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self.__call__(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return self.__call__(input)

    @staticmethod
    def name() -> str:
        return "local_ollama"

    def get_config(self) -> Dict[str, Any]:
        return {"host": self.host, "model": self.model}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "LocalOllamaEmbeddingFunction":
        return LocalOllamaEmbeddingFunction(
            host=config.get("host", "http://ollama:11434"),
            model=config.get("model", "nomic-embed-text")
        )


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
        ollama_host: str = "http://ollama:11434",
        embedding_model: str = "nomic-embed-text"
    ):
        self.persist_dir = persist_dir
        self.data_dir = data_dir
        self.collection_name = collection_name
        self.ollama_host = ollama_host
        self.embedding_model = embedding_model
        self.client: Optional[chromadb.PersistentClient] = None
        self.collection = None
        self.embedding_fn = None

    def initialize(self):
        """Initialize ChromaDB client and ingest knowledge base documents."""
        os.makedirs(self.persist_dir, exist_ok=True)
        logger.info("Initializing ChromaDB persistent client at %s", self.persist_dir)

        # Uses local Ollama GPU embeddings (nomic-embed-text)
        self.embedding_fn = LocalOllamaEmbeddingFunction(
            host=self.ollama_host,
            model=self.embedding_model
        )

        # In-process persistent ChromaDB instance
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"description": "Haniff Kamal Portfolio Knowledge Base"}
            )
        except ValueError as exc:
            if "Embedding function conflict" in str(exc):
                logger.info("Resetting collection due to embedding function upgrade to local Ollama...")
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_fn,
                    metadata={"description": "Haniff Kamal Portfolio Knowledge Base"}
                )
            else:
                raise

        # Ingest documents on startup
        self.ingest_markdown_files()

    def _chunk_markdown(self, filename: str, content: str) -> List[Dict[str, Any]]:
        """
        Split markdown content into semantic chunks based on headers.
        Prepending section titles to each chunk preserves semantic context during vector search.
        """
        chunks = []
        doc_title = os.path.basename(filename).replace(".md", "").capitalize()
        lines = content.split("\n")
        current_header = doc_title
        current_lines = []

        for line in lines:
            if line.startswith("## ") or line.startswith("### "):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append({
                            "text": f"[{doc_title} - {current_header}]\n{chunk_text}",
                            "source": os.path.basename(filename),
                            "section": current_header
                        })
                    current_lines = []
                current_header = line.lstrip("#").strip()
            else:
                current_lines.append(line)

        # Append final chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append({
                    "text": f"[{doc_title} - {current_header}]\n{chunk_text}",
                    "source": os.path.basename(filename),
                    "section": current_header
                })

        return chunks

    def ingest_markdown_files(self):
        """Read all .md files from data directory, chunk them, and index into ChromaDB."""
        search_pattern = os.path.join(self.data_dir, "*.md")
        files = glob.glob(search_pattern)

        if not files:
            logger.warning("No markdown files found in %s to index.", self.data_dir)
            return

        logger.info("Ingesting %d markdown files from %s...", len(files), self.data_dir)

        # Reset collection to prevent duplicate entries on restarts
        existing_count = self.collection.count()
        if existing_count > 0:
            logger.info("Refreshing collection (existing chunks: %d)", existing_count)
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
                metadata={"description": "Haniff Kamal Portfolio Knowledge Base"}
            )

        documents = []
        metadatas = []
        ids = []

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                chunks = self._chunk_markdown(file_path, content)
                base_name = os.path.basename(file_path).replace(".md", "")

                for idx, chunk in enumerate(chunks):
                    chunk_id = f"{base_name}_{idx}"
                    documents.append(chunk["text"])
                    metadatas.append({
                        "source": chunk["source"],
                        "section": chunk["section"]
                    })
                    ids.append(chunk_id)

            except Exception as exc:
                logger.error("Failed to parse markdown file %s: %s", file_path, exc)

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info("Successfully indexed %d chunks across %d documents into ChromaDB.", len(documents), len(files))

    def retrieve_context(self, query: str, n_results: int = 2) -> str:
        """
        Query ChromaDB for the most semantically relevant chunks matching user query.
        Returns a formatted string ready for LLM prompt augmentation.
        """
        if not self.collection or self.collection.count() == 0:
            logger.warning("ChromaDB collection is empty or not initialized.")
            return ""

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )

            retrieved_docs = results.get("documents", [[]])[0]
            if not retrieved_docs:
                return ""

            context_blocks = []
            for doc in retrieved_docs:
                context_blocks.append(f"---\n{doc}")

            return "\n\n".join(context_blocks)

        except Exception as exc:
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
            "3. Keep responses direct, professional, and well-structured.\n"
            "4. Do NOT make up or extrapolate facts not present in the context."
        )

        if context.strip():
            return f"{base_prompt}\n\n=== VERIFIED PORTFOLIO CONTEXT ===\n{context}\n================================="
        else:
            return base_prompt
