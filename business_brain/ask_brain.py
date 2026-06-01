"""
ask_brain.py — Query the Business Brain document index.

Supports two modes:
  1. Keyword search (fast, no LM Studio needed)
  2. Semantic search using embeddings (requires LM Studio running)
"""

import os
import json
import sys
import urllib.request
import urllib.error


def load_index(index_path: str = None) -> dict:
    """Load the document index from disk."""
    if index_path is None:
        index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "embeddings.json")
    if not os.path.exists(index_path):
        print(f"Index file not found: {index_path}")
        print("Run: python indexer.py")
        sys.exit(1)
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def keyword_search(query: str, index: dict, top_k: int = 5) -> list:
    """Fast keyword-based search over raw chunk text."""
    query_lower = query.lower()
    results = []

    for relpath, metadata in index.items():
        for chunk in metadata.get("chunks", []):
            text = chunk.get("text", "")
            score = text.lower().count(query_lower)
            if score > 0:
                results.append({
                    "file": relpath,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "score": score,
                    "text": text,
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def get_lm_studio_url() -> str:
    """Load LM Studio URL from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("lm_studio_url", "http://localhost:1234")
    except Exception:
        return "http://localhost:1234"


def get_embedding_model() -> str:
    """Load embedding model from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("embedding_model", "nomic-embed-text")
    except Exception:
        return "nomic-embed-text"


def semantic_search(query: str, index: dict, embedding_model: str, top_k: int = 5) -> list:
    """
    Semantic search: embed the query via LM Studio, then find closest chunks
    by cosine similarity.
    """
    lm_studio_url = get_lm_studio_url()
    endpoint = f"{lm_studio_url.rstrip('/')}/v1/embeddings"

    # Embed the query
    try:
        payload = json.dumps({"model": embedding_model, "input": query}).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        query_emb = result["data"][0]["embedding"]
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"LM Studio connection failed: {exc}")
        print("Falling back to keyword search.")
        return keyword_search(query, index, top_k)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        print(f"Could not parse LM Studio response: {exc}")
        print("Falling back to keyword search.")
        return keyword_search(query, index, top_k)

    # Cosine similarity against all chunks
    results = []
    for relpath, metadata in index.items():
        for chunk in metadata.get("chunks", []):
            chunk_emb = chunk.get("embedding", [])
            if not chunk_emb or all(v == 0 for v in chunk_emb):
                continue
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_emb, chunk_emb))
            mag_q = sum(a * a for a in query_emb) ** 0.5
            mag_c = sum(b * b for b in chunk_emb) ** 0.5
            if mag_q == 0 or mag_c == 0:
                continue
            similarity = dot / (mag_q * mag_c)
            if similarity > 0:
                results.append({
                    "file": relpath,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "score": round(similarity, 4),
                    "text": chunk.get("text", ""),
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def ask(query: str, index_path: str = None, use_semantic: bool = True) -> list:
    """Main entry point: search the index for the given query."""
    index = load_index(index_path)

    if not index:
        print("Index is empty. Run: python indexer.py")
        return []

    if use_semantic:
        embedding_model = get_embedding_model()
        return semantic_search(query, index, embedding_model)
    else:
        return keyword_search(query, index)


def display_results(results: list):
    """Pretty-print search results."""
    if not results:
        print("No results found.")
        return

    print(f"\n{'=' * 60}")
    print(f"Top {len(results)} result(s):\n")

    for i, result in enumerate(results, 1):
        print(f"--- Result {i} [{result['file']} chunk {result['chunk_index']}] (score: {result['score']}) ---")
        # Show first 500 chars of the matching chunk
        text = result["text"]
        if len(text) > 500:
            text = text[:500] + "..."
        print(text)
        print()

    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask_brain.py <query> [--keyword]")
        print("  --keyword   Force keyword search (no LM Studio needed)")
        sys.exit(1)

    use_semantic = "--keyword" not in sys.argv
    query = " ".join(arg for arg in sys.argv[1:] if arg != "--keyword")
    results = ask(query, use_semantic=use_semantic)
    display_results(results)
