"""
Ask Brain: Query the business document index for answers.
"""

import os
import json


def load_index(index_path: str) -> dict:
    """Load the document index from disk."""
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def search(query: str, index: dict, top_k: int = 5) -> list:
    """Simple keyword-based search over the index."""
    query_lower = query.lower()
    results = []

    for relpath, metadata in index.items():
        content = metadata.get("content", "")
        score = content.lower().count(query_lower)
        if score > 0:
            results.append((relpath, score, content))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def ask(query: str, index_path: str = None) -> list:
    """Main entry point: load index and search for the query."""
    if index_path is None:
        index_path = os.path.join(os.path.dirname(__file__), "embeddings.json")
    index = load_index(index_path)
    return search(query, index)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ask_brain.py <query>")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    results = ask(query)
    for relpath, score, content in results:
        print(f"\n--- {relpath} (score: {score}) ---")
        print(content[:500])
