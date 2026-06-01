"""
indexer.py — Business Brain Document Indexer

Walks through the /documents folder, extracts text from .txt/.pdf/.docx files,
splits text into ~500-token chunks, generates embeddings via LM Studio,
and saves everything to embeddings.json.

Requirements (pip install):
    pip install pdfplumber python-docx tiktoken

LM Studio requirement:
    - Install https://lmstudio.ai
    - Open LM Studio → Local Server tab
    - Load an embedding model (e.g. nomic-embed-text)
    - Click "Start Server" (default: http://localhost:1234)
"""

import os
import sys
import json
import hashlib
import time
import textwrap
import logging
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("indexer")

# ---------------------------------------------------------------------------
# Optional imports — fail gracefully
# ---------------------------------------------------------------------------
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    log.warning("pdfplumber not installed — PDF support disabled. pip install pdfplumber")

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    log.warning("python-docx not installed — DOCX support disabled. pip install python-docx")

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    log.warning("tiktoken not installed — falling back to char-based chunking")

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def load_config(config_path: str = None) -> dict:
    """Load config.json from the same directory as this script."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_embedding_model(config: dict) -> str:
    """Return the embedding model name, defaulting to nomic-embed-text."""
    return config.get("embedding_model", "nomic-embed-text")


def get_lm_studio_url(config: dict) -> str:
    """Return the LM Studio local server URL."""
    return config.get("lm_studio_url", "http://localhost:1234")


def get_documents_dir(config: dict) -> str:
    """Return the absolute path to the documents directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    rel = config.get("documents_dir", "documents")
    return os.path.join(base, rel)


def get_index_path(config: dict) -> str:
    """Return the absolute path to embeddings.json."""
    base = os.path.dirname(os.path.abspath(__file__))
    rel = config.get("index_file", "embeddings.json")
    return os.path.join(base, rel)

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def extract_text_txt(filepath: str) -> str:
    """Extract text from a plain .txt file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_text_pdf(filepath: str) -> str:
    """Extract text from a .pdf file using pdfplumber."""
    if not HAS_PDF:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")
    pages = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
    except Exception as exc:
        raise RuntimeError(f"Failed to read PDF '{filepath}': {exc}")
    return "\n\n".join(pages)


def extract_text_docx(filepath: str) -> str:
    """Extract text from a .docx file using python-docx."""
    if not HAS_DOCX:
        raise RuntimeError("python-docx is not installed. Run: pip install python-docx")
    try:
        doc = docx.Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:
        raise RuntimeError(f"Failed to read DOCX '{filepath}': {exc}")


def extract_text(filepath: str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".txt":
        return extract_text_txt(filepath)
    elif ext == ".pdf":
        return extract_text_pdf(filepath)
    elif ext == ".docx":
        return extract_text_docx(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def count_tokens(text: str, model_name: str = "nomic-embed-text") -> int:
    """Estimate token count for *text* using tiktoken if available."""
    if HAS_TIKTOKEN:
        try:
            enc = tiktoken.encoding_for_model("gpt-4o")  # universal fallback
            return len(enc.encode(text))
        except Exception:
            pass
    # Fallback: rough estimate — ~4 chars per token (common for most models)
    return max(1, len(text) // 4)


def chunk_text(text: str, chunk_size_tokens: int = 500, overlap_tokens: int = 50) -> list:
    """Split *text* into overlapping chunks of roughly *chunk_size_tokens* tokens."""
    if HAS_TIKTOKEN:
        enc = tiktoken.encoding_for_model("gpt-4o")
        tokens = enc.encode(text)
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(enc.decode(chunk_tokens))
            start += chunk_size_tokens - overlap_tokens
            if start >= len(tokens):
                break
        return chunks
    else:
        # Fallback: char-based chunking (~4 chars ≈ 1 token)
        chunk_chars = chunk_size_tokens * 4
        overlap_chars = overlap_tokens * 4
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_chars, len(text))
            # Try to break at a sentence boundary
            break_point = text.rfind("\n\n", start, end)
            if break_point > start:
                end = break_point
            chunks.append(text[start:end])
            # Advance: use the next chunk's start, but never go backwards
            next_start = start + chunk_chars - overlap_chars
            if next_start <= start:
                next_start = start + 1
            start = next_start
            if start >= len(text):
                break
        return chunks

# ---------------------------------------------------------------------------
# Embedding via LM Studio (HTTP API)
# ---------------------------------------------------------------------------

def generate_embedding_with_lm_studio(text: str, model: str, url: str) -> list:
    """
    Call LM Studio's local /v1/embeddings endpoint and return the embedding vector.

    LM Studio runs a local OpenAI-compatible server (default: http://localhost:1234).
    We POST to /v1/embeddings with the model and input, then parse the response.
    """
    endpoint = f"{url.rstrip('/')}/v1/embeddings"
    payload = {
        "model": model,
        "input": text,
    }
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # LM Studio returns: {"data": [{"embedding": [...]}]}
        if isinstance(result, dict) and "data" in result and len(result["data"]) > 0:
            return result["data"][0]["embedding"]
        raise RuntimeError(f"Unexpected LM Studio response format: {result}")

    except urllib.error.URLError as exc:
        raise RuntimeError(f"LM Studio connection failed: {exc}. Is the local server running?")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse LM Studio response: {exc}")
    except TimeoutError:
        raise RuntimeError("LM Studio request timed out after 120s")


def generate_embeddings_for_chunks(chunks: list, model: str, url: str) -> list:
    """Generate embeddings for a list of text chunks via LM Studio, with progress logging."""
    embeddings = []
    for i, chunk in enumerate(chunks):
        try:
            emb = generate_embedding_with_lm_studio(chunk, model, url)
            embeddings.append(emb)
            if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                log.info(f"  Generated {i + 1}/{len(chunks)} embeddings")
        except Exception as exc:
            log.error(f"  Embedding failed for chunk {i + 1}: {exc}")
            # Append a zero-vector as a placeholder so we don't lose the chunk
            embeddings.append([0.0] * 768)  # nomic-embed-text default dim
            if i == 0:
                # Guess the dimension from the first failure
                pass
    return embeddings

# ---------------------------------------------------------------------------
# Main indexing pipeline
# ---------------------------------------------------------------------------

def walk_documents(documents_dir: str) -> list:
    """Walk the documents directory and return list of (relpath, abs_path) tuples."""
    files = []
    for root, _, filenames in os.walk(documents_dir):
        for filename in sorted(filenames):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, documents_dir)
                files.append((rel_path, abs_path))
    return files


def index_documents(
    config: dict = None,
    force_reindex: bool = False,
) -> dict:
    """
    Main indexing pipeline:
      1. Walk documents directory
      2. Extract text (txt/pdf/docx)
      3. Chunk into ~500-token pieces
      4. Generate embeddings via LM Studio
      5. Save to embeddings.json
    """
    if config is None:
        config = load_config()

    documents_dir = get_documents_dir(config)
    index_path = get_index_path(config)
    embedding_model = get_embedding_model(config)
    lm_studio_url = get_lm_studio_url(config)
    chunk_size = config.get("chunk_size_tokens", 500)
    overlap = config.get("chunk_overlap_tokens", 50)

    log.info("=" * 60)
    log.info("Business Brain Indexer — Starting")
    log.info(f"  Documents dir    : {documents_dir}")
    log.info(f"  Embedding model  : {embedding_model}")
    log.info(f"  LM Studio URL    : {lm_studio_url}")
    log.info(f"  Chunk size       : ~{chunk_size} tokens")
    log.info(f"  Output file      : {index_path}")
    log.info("=" * 60)

    # Verify LM Studio local server is running
    try:
        endpoint = f"{lm_studio_url.rstrip('/')}/v1/models"
        req = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"LM Studio responded with status {resp.status}")
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        log.error(f"LM Studio local server is not reachable: {exc}")
        log.error("Open LM Studio → Local Server tab → Start Server")
        sys.exit(1)

    # Load existing index for incremental updates
    existing_index = {}
    if os.path.exists(index_path) and not force_reindex:
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                existing_index = json.load(f)
            log.info(f"Loaded existing index with {len(existing_index)} entries")
        except (json.JSONDecodeError, IOError) as exc:
            log.warning(f"Could not load existing index: {exc}. Starting fresh.")

    # Walk documents
    files = walk_documents(documents_dir)
    if not files:
        log.warning(f"No supported files found in {documents_dir}")
        log.info("Supported extensions: .txt, .pdf, .docx")
        return {}

    log.info(f"Found {len(files)} file(s) to process\n")

    new_index = {}
    stats = {"indexed": 0, "skipped": 0, "errors": 0}

    for rel_path, abs_path in files:
        log.info(f"[{stats['indexed'] + stats['skipped'] + 1}/{len(files)}] Processing: {rel_path}")

        # Check if file is unchanged (incremental update)
        try:
            file_hash = hashlib.md5(open(abs_path, "rb").read()).hexdigest()
        except IOError as exc:
            log.error(f"  Cannot read file: {exc}")
            stats["errors"] += 1
            stats["skipped"] += 1
            continue

        if not force_reindex and rel_path in existing_index:
            old_hash = existing_index[rel_path].get("file_hash", "")
            if old_hash == file_hash:
                log.info(f"  Unchanged — skipping")
                stats["skipped"] += 1
                new_index[rel_path] = existing_index[rel_path]
                continue

        # Extract text
        try:
            text = extract_text(abs_path)
        except (RuntimeError, ValueError) as exc:
            log.error(f"  Text extraction failed: {exc}")
            stats["errors"] += 1
            stats["skipped"] += 1
            continue

        if not text or not text.strip():
            log.warning(f"  File is empty or contains no text — skipping")
            stats["skipped"] += 1
            continue

        log.info(f"  Extracted {len(text):,} chars")

        # Chunk
        chunks = chunk_text(text, chunk_size_tokens=chunk_size, overlap_tokens=overlap)
        log.info(f"  Split into {len(chunks)} chunk(s)")

        # Embed
        log.info(f"  Generating embeddings with '{embedding_model}'...")
        embeddings = generate_embeddings_for_chunks(chunks, embedding_model, lm_studio_url)

        # Build entry
        entry = {
            "file_path": abs_path,
            "file_hash": file_hash,
            "file_size_bytes": os.path.getsize(abs_path),
            "total_chars": len(text),
            "num_chunks": len(chunks),
            "chunks": [],
        }
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            entry["chunks"].append({
                "chunk_index": i,
                "text": chunk,
                "embedding": emb,
                "token_count": count_tokens(chunk),
            })

        new_index[rel_path] = entry
        stats["indexed"] += 1
        log.info(f"  ✓ Done\n")

    # Save index
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(new_index, f, indent=2, ensure_ascii=False)
        log.info("=" * 60)
        log.info(f"Indexed {stats['indexed']} file(s), skipped {stats['skipped']}, errors {stats['errors']}")
        log.info(f"Total chunks indexed: {sum(e['num_chunks'] for e in new_index.values())}")
        log.info(f"Index saved to: {index_path}")
        log.info("=" * 60)
    except IOError as exc:
        log.error(f"Failed to save index: {exc}")
        sys.exit(1)

    return new_index

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Business Brain Document Indexer — extract text, chunk, embed, and index documents.",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force re-index all files (ignore unchanged files)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.json (default: config.json in this directory)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    index_documents(config, force_reindex=args.reindex)
