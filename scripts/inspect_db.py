#!/usr/bin/env python3
# ==============================================================================
# ChromaDB Inspector CLI: View & Query In-Process Vector Store
# ==============================================================================
# Usage:
#   docker exec -it chatbot-backend python3 scripts/inspect_db.py
#   docker exec -it chatbot-backend python3 scripts/inspect_db.py -q "deepfake research"
# ==============================================================================

import argparse
import os
import sys

# Support execution inside container (/app) or on host relative to repository root
sys.path.insert(0, "/app")
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

import chromadb
from chromadb.utils import embedding_functions


def inspect_chroma(query: str | None = None):
    print("\n" + "=" * 60)
    print("🔍 ChromaDB Vector Database Inspector")
    print("=" * 60)

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_db")
    client = chromadb.PersistentClient(path=persist_dir)

    from typing import Any

    embedding_fn: Any = embedding_functions.DefaultEmbeddingFunction()

    try:
        collection = client.get_collection(
            name="portfolio_knowledge", embedding_function=embedding_fn
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Could not load collection 'portfolio_knowledge': {exc}")
        return

    count = collection.count()
    print(f"📊 Storage Location : {persist_dir}")
    print("📦 Collection Name  : portfolio_knowledge")
    print(f"📑 Total Chunks     : {count}\n")

    if count == 0:
        print("⚠️  No chunks found in database.")
        return

    # If query provided, run semantic search
    if query:
        print(f"🔎 Testing Semantic Query: '{query}'")
        print("-" * 60)
        results = collection.query(query_texts=[query], n_results=min(3, count))
        raw_docs = results.get("documents")
        docs = raw_docs[0] if raw_docs else []
        raw_metas = results.get("metadatas")
        metas = raw_metas[0] if raw_metas else []
        raw_distances = results.get("distances")
        distances = raw_distances[0] if raw_distances else [0.0] * len(docs)

        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            source = meta.get("source") if isinstance(meta, dict) else "unknown"
            section = meta.get("section") if isinstance(meta, dict) else "unknown"
            print(f"\n[Match #{i + 1}] (Distance: {dist:.4f})")
            print(f"Source  : {source} | Section: {section}")
            print(f"Content :\n{doc.strip()}")
            print("-" * 40)
        return

    # Otherwise, list all chunks in the database
    data = collection.get(include=["documents", "metadatas"])
    print("📚 Stored Knowledge Chunks:")
    print("-" * 60)

    ids = data.get("ids", [])
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []

    for i, (cid, doc, meta) in enumerate(zip(ids, documents, metadatas)):
        source = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
        section = (
            meta.get("section", "unknown") if isinstance(meta, dict) else "unknown"
        )
        preview = doc.strip().replace("\n", " ")[:90]

        print(
            f"[{i + 1:02d}] ID: {cid:<15} | Source: {source:<12} | Section: {section}"
        )
        print(f"     Preview: {preview}...")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect ChromaDB contents")
    parser.add_argument(
        "--query", "-q", type=str, default=None, help="Semantic search test query"
    )
    args = parser.parse_args()
    inspect_chroma(query=args.query)
