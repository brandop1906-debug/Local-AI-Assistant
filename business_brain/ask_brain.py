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


def get_lm_studio_chat_url() -> str:
    """Load LM Studio chat URL from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("lm_studio_chat_url", None)
    except Exception:
        return None


def get_llm_model() -> str:
    """Load LLM model name from config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config.get("llm_model", "local-model")
    except Exception:
        return "local-model"


def generate_answer(query: str, context_chunks: list, lm_studio_url: str = None) -> str:
    """
    Send the query and retrieved context chunks to the local LLM
    via LM Studio and return a clean, helpful answer.
    """
    if lm_studio_url is None:
        lm_studio_url = get_lm_studio_chat_url()

    # Build the context from retrieved chunks
    context = ""
    for i, chunk in enumerate(context_chunks, 1):
        context += f"[Document {i}] {chunk['text']}\n"

    # Construct the prompt with system and user messages
    system_prompt = (
        "You are a helpful assistant. Use the provided context to answer the user's "
        "question. If the context doesn't contain enough information, say so clearly. "
        "Be concise and accurate."
    )
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    # Build the chat API payload
    payload = {
        "model": get_llm_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            lm_studio_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        # Extract the assistant's response
        answer = result["choices"][0]["message"]["content"].strip()
        return answer
    except (urllib.error.URLError, TimeoutError) as exc:
        return (
            f"Could not reach LM Studio at {lm_studio_url}: {exc}. "
            "Please ensure LM Studio is running with a chat model loaded."
        )
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        return f"Error parsing LLM response: {exc}"
    except Exception as exc:
        return f"Unexpected error calling LLM: {exc}"


def ask(query: str, index_path: str = None, use_semantic: bool = True):
    """
    Main entry point: search the index and generate an answer.

    1. Load embeddings.json
    2. Compute similarity between the question and all chunks
    3. Select the top 3 most relevant chunks
    4. Send them to a local LLM via LM Studio
    5. Return a clean, helpful answer
    """
    index = load_index(index_path)

    if not index:
        print("Index is empty. Run: python indexer.py")
        return "No index available. Please run the indexer first."

    # Determine top_k — always retrieve 5 for context, return top 3 to LLM
    top_k = 5

    if use_semantic:
        embedding_model = get_embedding_model()
        results = semantic_search(query, index, embedding_model, top_k=top_k)
    else:
        results = keyword_search(query, index, top_k=top_k)

    if not results:
        return "No relevant context found. Please check your index or try a different query."

    # Select the top 3 most relevant chunks to send to the LLM
    top_chunks = results[:3]

    # Generate an answer using the local LLM
    lm_studio_url = get_lm_studio_chat_url()
    if lm_studio_url:
        answer = generate_answer(query, top_chunks, lm_studio_url)
    else:
        # Fallback: return the raw context if no chat endpoint configured
        answer = (
            f"Query: {query}\n\n"
            "Relevant context (no LLM configured):\n"
            + "\n---\n".join(
                f"[Chunk {c['chunk_index']}] {c['text']}" for c in top_chunks
            )
        )

    return answer


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask_brain.py <query> [--keyword]")
        print("  --keyword   Force keyword search (no LM Studio needed)")
        sys.exit(1)

    use_semantic = "--keyword" not in sys.argv
    query = " ".join(arg for arg in sys.argv[1:] if arg != "--keyword")
    answer = ask(query, use_semantic=use_semantic)
    print(answer)
