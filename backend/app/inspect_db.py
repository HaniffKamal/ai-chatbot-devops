#!/usr/bin/env python3
# ==============================================================================
# ChromaDB Inspector CLI: View & Query In-Process Vector Store
# ==============================================================================
# Usage:
#   docker exec -it chatbot-backend python3 -m app.inspect_db
#   docker exec -it chatbot-backend python3 -m app.inspect_db --query "deepfake research"
# ==============================================================================

import sys
import argparse
import chromadb
from app.rag import LocalOllamaEmbeddingFunction

def inspect_chroma(query: str = None):
    print("\n" + "=" * 60)
    print("🔍 ChromaDB Vector Database Inspector")
    print("=" * 60)

    persist_dir = "/app/chroma_db"
    client = chromadb.PersistentClient(path=persist_dir)

    embedding_fn = LocalOllamaEmbeddingFunction(
        host="http://ollama:11434",
        model="nomic-embed-text"
    )

    try:
        collection = client.get_collection(
            name="portfolio_knowledge",
            embedding_function=embedding_fn
        )
    except Exception as exc:
        print(f"❌ Could not load collection 'portfolio_knowledge': {exc}")
        return

    count = collection.count()
    print(f"📊 Storage Location : {persist_dir}")
    print(f"📦 Collection Name  : portfolio_knowledge")
    print(f"📑 Total Chunks     : {count}\n")

    if count == 0:
        print("⚠️  No chunks found in database.")
        return

    # If query provided, run semantic search
    if query:
        print(f"🔎 Testing Semantic Query: '{query}'")
        print("-" * 60)
        results = collection.query(query_texts=[query], n_results=min(3, count))
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0]*len(docs)

        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
            print(f"\n[Match #{i+1}] (Distance: {dist:.4f})")
            print(f"Source  : {meta.get('source')} | Section: {meta.get('section')}")
            print(f"Content :\n{doc.strip()}")
            print("-" * 40)
        return

    # Otherwise, list all chunks in the database
    data = collection.get(include=["documents", "metadatas"])
    print("📚 Stored Knowledge Chunks:")
    print("-" * 60)

    for i, (cid, doc, meta) in enumerate(zip(data["ids"], data["documents"], data["metadatas"])):
        source = meta.get("source", "unknown")
        section = meta.get("section", "unknown")
        first_line = doc.strip().split("\n")[0]
        preview = doc.strip().replace("\n", " ")[:90]

        print(f"[{i+1:02d}] ID: {cid:<15} | Source: {source:<12} | Section: {section}")
        print(f"     Preview: {preview}...")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect ChromaDB contents")
    parser.add_argument("--query", "-q", type=str, default=None, help="Semantic search test query")
    args = parser.parse_args()
    inspect_chroma(query=args.query)
