"""
chat_ai/rag.py
==============
Retrieval-Augmented Generation (RAG) module for the Local AI Assistant.

Wires chat_ai up to the existing business_brain semantic search.
Instead of dumping all documents into the prompt, it:

  1. Takes the user's question
  2. Embeds it using the same model as business_brain
  3. Finds the top-K most relevant chunks via cosine similarity
  4. Injects only those chunks into the system prompt
  5. Sends to LLM

This is much more efficient and scalable than loading all documents.

Usage:
    from chat_ai.rag import retrieve_context
    chunks = retrieve_context("What is the pricing structure?", top_k=5)
"""

import json
import os
import math
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MODULE_DIR = Path(__file__).resolve().parent
# chat_ai is inside modules/, go up TWO levels to reach project root
_PROJECT_ROOT = _MODULE_DIR.parent.parent
_BRAIN_DIR = _PROJECT_ROOT / "business_brain"


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _load_brain_config() -> dict:
    """Load business_brain config.json for model/URL settings."""
    config_path = _BRAIN_DIR / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _load_index() -> dict:
    """Load the business_brain embeddings index."""
    index_path = _BRAIN_DIR / "embeddings.json"
    if not index_path.exists():
        return {}
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _get_embedding_config() -> tuple:
    """Return (model_name, lm_studio_url) from business_brain config."""
    config = _load_brain_config()
    model = config.get("embedding_model", "nomic-embed-text")
    url = config.get("lm_studio_url", "http://localhost:1234")
    return model, url


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed_text(text: str, model: str, url: str) -> list:
    """Call LM Studio's /v1/embeddings endpoint and return the embedding vector."""
    endpoint = f"{url.rstrip('/')}/v1/embeddings"
    payload = {"model": model, "input": text}
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if isinstance(result, dict) and "data" in result and len(result["data"]) > 0:
            return result["data"][0]["embedding"]
        raise RuntimeError(f"Unexpected embedding response: {result}")
    except urllib.error.URLError:
        return None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Index flattening
# ---------------------------------------------------------------------------

def _flatten_index(index: dict) -> list:
    """
    Flatten the hierarchical index into a list of (file, chunk_index, text, embedding) tuples.
    """
    results = []
    for relpath, file_data in index.items():
        file_path = file_data.get("file_path", relpath)
        for chunk in file_data.get("chunks", []):
            chunk_text = chunk.get("text", "")
            chunk_emb = chunk.get("embedding", [])
            if chunk_text and chunk_emb and any(v != 0 for v in chunk_emb):
                results.append({
                    "file": relpath,
                    "file_path": file_path,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "text": chunk_text,
                    "embedding": chunk_emb,
                    "token_count": chunk.get("token_count", 0),
                })
    return results


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------

def semantic_search(query: str, top_k: int = 5) -> list:
    """
    Perform semantic search across the business_brain document index.

    Args:
        query: The user's question/search term.
        top_k: Number of relevant chunks to return.

    Returns:
        list of dicts with keys: file, file_path, chunk_index, text, score
    """
    index = _load_index()
    if not index:
        return []

    model, url = _get_embedding_config()
    query_emb = _embed_text(query, model, url)
    if query_emb is None:
        return []

    # Flatten and score all chunks
    flat = _flatten_index(index)
    scored = []
    for chunk_info in flat:
        sim = _cosine_similarity(query_emb, chunk_info["embedding"])
        if sim > 0:
            scored.append({
                "file": chunk_info["file"],
                "file_path": chunk_info["file_path"],
                "chunk_index": chunk_info["chunk_index"],
                "text": chunk_info["text"],
                "score": round(sim, 4),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------------------
# RAG context building
# ---------------------------------------------------------------------------

def retrieve_context(query: str, top_k: int = 5, max_context_chars: int = 6000) -> str:
    """
    Retrieve relevant document chunks for a query and format them as context.

    This is the core RAG function: embed the query, find top-K chunks,
    and format them into a context string for the LLM.

    Args:
        query: The user's question.
        top_k: Number of chunks to retrieve.
        max_context_chars: Soft limit on total context character count.

    Returns:
        str: Formatted context string, or empty string if no context found.
    """
    results = semantic_search(query, top_k=top_k)
    if not results:
        return ""

    # Format chunks as context
    context_parts = []
    total_chars = 0
    for i, chunk in enumerate(results, 1):
        chunk_text = chunk["text"]
        # Respect the char limit
        if total_chars + len(chunk_text) > max_context_chars:
            remaining = max_context_chars - total_chars
            if remaining > 100:
                chunk_text = chunk_text[:remaining] + "..."
            else:
                break
        context_parts.append(
            f"[Source: {chunk['file']} (chunk {chunk['chunk_index']}) | "
            f"relevance: {chunk['score']:.3f}]\n{chunk_text}"
        )
        total_chars += len(chunk_text)

    return "\n\n---\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# RAG-aware context builder (replaces the old dump-all approach)
# ---------------------------------------------------------------------------

def build_rag_context(query: str, top_k: int = 5, max_context_chars: int = 6000) -> str:
    """
    Build a RAG-aware context string for a specific query.

    This replaces the old approach of dumping all documents into the
    system prompt. Instead, it only retrieves and includes the most
    relevant chunks for the current question.

    Args:
        query: The user's question.
        top_k: Number of relevant chunks to retrieve.
        max_context_chars: Soft limit on total context size.

    Returns:
        str: A formatted context string with project metadata + retrieved chunks.
    """
    # Always include a small amount of project metadata
    project_info = _build_project_metadata()

    # Retrieve relevant chunks via RAG
    retrieved = retrieve_context(query, top_k=top_k, max_context_chars=max_context_chars)

    if retrieved:
        return (
            f"=== PROJECT CONTEXT ===\n\n"
            f"{project_info}\n\n"
            f"=== Retrieved Context (for your question) ===\n\n"
            f"{retrieved}\n\n"
            f"=== END CONTEXT ==="
        )
    else:
        return (
            f"=== PROJECT CONTEXT ===\n\n"
            f"{project_info}\n\n"
            f"=== No relevant context found in documents ===\n\n"
            f"=== END CONTEXT ==="
        )


def _build_project_metadata() -> str:
    """Build a small project metadata block (always included)."""
    parts = [
        "Local AI Assistant is a desktop application that provides AI-powered",
        "tools for business automation. All processing happens locally.",
        "",
        "## Available Modules:",
    ]

    launcher_config = _PROJECT_ROOT / "config.json"
    if launcher_config.exists():
        try:
            with open(launcher_config, "r", encoding="utf-8") as f:
                config = json.load(f)
            for mod in config.get("modules", []):
                parts.append(f"- **{mod['name']}**: {mod['path']}")
        except Exception:
            pass

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rag.py <query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Query: {query}\n")

    context = build_rag_context(query, top_k=5)
    print(context)
