"""
pdf_summarizer.py
=================
A local, offline PDF summarizer powered by LM Studio.

This script:
  1. Accepts a PDF file (via command-line argument or drag-and-drop)
  2. Extracts all text from the PDF
  3. Splits the text into manageable chunks if needed
  4. Sends each chunk to a local LM Studio model for summarization
  5. Combines chunk summaries into a clean bullet-point summary
  6. Saves the summary to /output with a timestamped filename

No cloud APIs required. Everything runs on your machine.

Requirements:
  - Python 3.8+
  - LM Studio installed and running: https://lmstudio.ai
  - A model loaded in LM Studio with the Local Server started
  - Optional: pip install pdfplumber (preferred), PyPDF2 (fallback)

Usage:
  python pdf_summarizer.py path/to/your/file.pdf
  # or drag and drop a PDF onto this script

Output:
  Summaries are saved to the /output folder as:
    summary_YYYYMMDD_HHMMSS.txt
"""

import os
import sys
import json
import textwrap
from datetime import datetime

# Force UTF-8 encoding on Windows (fixes emoji print crashes)
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Configuration – loads from config.json, falls back to defaults
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# Sensible defaults (used when config.json is missing or invalid)
DEFAULT_CONFIG = {
    "model": "qwen/qwen3.6-35b-a3b",
    "lm_studio_host": "http://127.0.0.1:1234",
    "output_folder": "output",
    "chunk_size": 4000,
    "temperature": 0.3,
    "max_tokens": 2048,
}


def load_config() -> dict:
    """
    Load configuration from config.json, with environment variable overrides.

    Priority (highest to lowest):
      1. Environment variables (e.g. LM_STUDIO_HOST)
      2. config.json values
      3. DEFAULT_CONFIG fallbacks

    Returns:
        A config dictionary.
    """
    config = dict(DEFAULT_CONFIG)

    # 1. Load from config.json if it exists
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            if isinstance(file_config, dict):
                # Only accept known keys to avoid surprises
                for key in DEFAULT_CONFIG:
                    if key in file_config:
                        config[key] = file_config[key]
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Failed to load {CONFIG_PATH}: {e}. Using defaults.")

    # 2. Environment variable overrides (highest priority)
    env_host = os.environ.get("LM_STUDIO_HOST")
    if env_host:
        config["lm_studio_host"] = env_host

    env_model = os.environ.get("LM_STUDIO_MODEL")
    if env_model:
        config["model"] = env_model

    env_temp = os.environ.get("LM_TEMPERATURE")
    if env_temp is not None:
        try:
            config["temperature"] = float(env_temp)
        except ValueError:
            pass

    env_max = os.environ.get("LM_MAX_TOKENS")
    if env_max is not None:
        try:
            config["max_tokens"] = int(env_max)
        except ValueError:
            pass

    env_chunk = os.environ.get("LM_CHUNK_SIZE")
    if env_chunk is not None:
        try:
            config["chunk_size"] = int(env_chunk)
        except ValueError:
            pass

    return config


# Load config at module import time
CONFIG = load_config()

# Expose as module-level variables
MODEL = CONFIG["model"]
LM_STUDIO_HOST = CONFIG["lm_studio_host"]
CHUNK_SIZE = CONFIG["chunk_size"]
TEMPERATURE = CONFIG["temperature"]
MAX_TOKENS = CONFIG["max_tokens"]
OUTPUT_DIR = os.path.join(SCRIPT_DIR, CONFIG["output_folder"])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """Create the directory if it doesn't exist (silent if it does)."""
    os.makedirs(path, exist_ok=True)


def extract_text_pdfplumber(pdf_path: str) -> str:
    """
    Extract text from a PDF using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a string.
    """
    import pdfplumber
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_pypdf2(pdf_path: str) -> str:
    """
    Extract text from a PDF using PyPDF2 (fallback if pdfplumber unavailable).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a string.
    """
    import PyPDF2
    text_parts = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text(pdf_path: str) -> str:
    """
    Extract text from a PDF, trying pdfplumber first, then PyPDF2.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text as a string.

    Raises:
        ImportError: If neither pdfplumber nor PyPDF2 is installed.
        FileNotFoundError: If the PDF file doesn't exist.
        Exception: If extraction fails.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Try pdfplumber first (better accuracy for most PDFs)
    try:
        return extract_text_pdfplumber(pdf_path)
    except ImportError:
        pass
    except Exception as e:
        print(f"  [WARN] pdfplumber failed: {e}")

    # Fallback to PyPDF2
    try:
        return extract_text_pypdf2(pdf_path)
    except ImportError:
        raise ImportError(
            "Neither pdfplumber nor PyPDF2 is installed.\n"
            "Install one with:\n"
            "  pip install pdfplumber    # preferred\n"
            "  pip install PyPDF2        # fallback"
        )


def split_into_chunks(text: str, chunk_size: int = 4000) -> list:
    """
    Split text into chunks, breaking at paragraph boundaries when possible.

    Args:
        text: The full text to split.
        chunk_size: Maximum characters per chunk.

    Returns:
        A list of text chunks.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    current_chunk = []
    current_length = 0

    for line in text.split("\n"):
        line_length = len(line) + 1  # +1 for the newline

        # If a single line is longer than chunk_size, force split it
        if line_length > chunk_size and current_length == 0:
            # Split the long line into smaller pieces
            words = line.split()
            for word in words:
                if current_length + len(word) + 1 > chunk_size:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                current_chunk.append(word)
                current_length += len(word) + 1
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_length = 0
            continue

        # If adding this line exceeds the chunk size, start a new chunk
        if current_length + line_length > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def call_lm_studio(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    """
    Send a prompt to LM Studio's local OpenAI-compatible API.

    Args:
        prompt: The full prompt string to send to LM Studio.
        model: The model name to use.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        The model's response as a string.

    Raises:
        RuntimeError: If LM Studio is not running or returns an error.
    """
    # Build the OpenAI-compatible chat request
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    url = f"{LM_STUDIO_HOST}/v1/chat/completions"

    # Try using requests first (preferred)
    try:
        import requests
        response = requests.post(url, json=payload, timeout=120)
    except ImportError:
        # Fallback: use urllib (built-in, no pip install needed)
        import urllib.request
        import urllib.error
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_text = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to LM Studio at {LM_STUDIO_HOST}.\n"
                f"Please make sure:\n"
                f"  1. LM Studio is running\n"
                f"  2. A model is loaded\n"
                f"  3. The Local Server is started (bottom-left icon)\n"
                f"  4. The port matches LM_STUDIO_HOST (default: 1234)"
            )
        # Parse the urllib response manually
        try:
            data = json.loads(response_text)
            return data["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(
                f"LM Studio returned unexpected data:\n{response_text}\n"
                f"Error: {e}"
            )

    # Parse the requests response
    if response.status_code != 200:
        raise RuntimeError(
            f"LM Studio returned status {response.status_code}:\n{response.text}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise RuntimeError(
            f"LM Studio returned unexpected data:\n{response.text}\nError: {e}"
        )


def check_lm_studio_running() -> bool:
    """
    Check if LM Studio's local server is reachable.

    Tries multiple endpoints in order of reliability:
      1. /v1/models       – OpenAI-compatible models list
      2. /health          – Simple health ping
      3. Root /           – Bare connection test

    Returns:
        True if the server responds, False otherwise.
    """
    endpoints = [
        f"{LM_STUDIO_HOST}/v1/models",
        f"{LM_STUDIO_HOST}/health",
        f"{LM_STUDIO_HOST}/",
    ]

    # Try requests first (preferred)
    try:
        import requests
        for url in endpoints:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False
    except ImportError:
        pass

    # Fallback: urllib
    try:
        import urllib.request
        for url in endpoints:
            try:
                resp = urllib.request.urlopen(url, timeout=10)
                if resp.status == 200:
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


def summarize_with_lm_studio(chunk_text: str, summary_length: str = "medium") -> str:
    """
    Send a text chunk to LM Studio for summarization.

    Args:
        chunk_text: The text chunk to summarize.
        summary_length: Desired output length – "short", "medium", or "detailed".

    Returns:
        The model's summary of the chunk.

    Raises:
        RuntimeError: If LM Studio is not running or the request fails.
    """
    length_instructions = {
        "short": "Keep it very brief – 3 to 5 key bullet points only.",
        "medium": "Keep it concise but comprehensive – 5 to 10 key bullet points.",
        "detailed": "Be thorough – include all key ideas, facts, and nuances in detailed bullet points.",
    }
    instruction = length_instructions.get(summary_length, length_instructions["medium"])

    prompt = (
        "You are a helpful summarization assistant. "
        f"{instruction} "
        "Focus on the key ideas, facts, and conclusions.\n\n"
        "---TEXT---\n"
        f"{chunk_text}\n"
        "---END---\n\n"
        "Provide your summary as bullet points:"
    )

    return call_lm_studio(prompt, MODEL, TEMPERATURE, MAX_TOKENS)


def combine_summaries(chunk_summaries: list, plain_english: bool = False) -> str:
    """
    Combine individual chunk summaries into a single cohesive summary.

    Args:
        chunk_summaries: List of per-chunk summaries.
        plain_english: If True, rewrite the final summary in simple, plain English.

    Returns:
        A combined, deduplicated bullet-point summary.
    """
    if len(chunk_summaries) == 1:
        result = chunk_summaries[0]
    else:
        # Combine all summaries and send to LM Studio for final consolidation
        combined_text = "\n\n".join(chunk_summaries)

        prompt = (
            "I have summaries from multiple chunks of the same document. "
            "Combine them into one clean, non-repetitive bullet-point summary. "
            "Remove any duplicate points and organize by topic.\n\n"
            "---CHUNK SUMMARIES---\n"
            f"{combined_text}\n"
            "---END---\n\n"
            "Final combined summary:"
        )

        try:
            result = call_lm_studio(prompt, MODEL, TEMPERATURE, MAX_TOKENS)
        except Exception as e:
            # If final consolidation fails, just join with separators
            print(f"  [WARN] Could not combine summaries: {e}")
            result = "\n\n" + "=" * 50 + "\n\n".join(chunk_summaries)

    # Optional plain-English rewrite
    if plain_english:
        rewrite_prompt = (
            "Please rewrite the following summary in simple, plain English. "
            "Use short sentences, everyday words, and avoid jargon or technical terms. "
            "Imagine explaining it to someone with no background in the topic. "
            "Keep the same meaning and key points, just make it easy to understand.\n\n"
            "---SUMMARY---\n"
            f"{result}\n"
            "---END---\n\n"
            "Rewritten in plain English:"
        )
        try:
            result = call_lm_studio(rewrite_prompt, MODEL, TEMPERATURE, MAX_TOKENS)
        except Exception as e:
            print(f"  [WARN] Plain English rewrite failed: {e}")

    return result


def save_summary(content: str, filename_prefix: str = "summary") -> str:
    """
    Save the summary to the output folder with a timestamped filename.

    Args:
        content: The summary text to save.
        filename_prefix: Prefix for the output filename.

    Returns:
        The full path to the saved file.
    """
    ensure_dir(OUTPUT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def summarize_pdf(pdf_path: str, *, progress_callback=None, summary_length="medium", plain_english=False) -> str:
    """
    Full pipeline: extract text -> chunk -> summarize -> combine -> save.

    Args:
        pdf_path: Path to the input PDF file.
        progress_callback: Optional callable(status, progress, total) for GUI updates.
        summary_length: Desired output length – "short", "medium", or "detailed".
        plain_english: If True, rewrite the final summary in simple, plain English.

    Returns:
        The path to the saved summary file.
    """
    print()
    print("=" * 60)
    print("       [PDF] PDF Summarizer (powered by LM Studio)")
    print("=" * 60)
    print()

    # --- Step 1: Validate input ---
    pdf_path = os.path.abspath(pdf_path)
    print(f"[PDF] Input PDF: {pdf_path}")

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if not pdf_path.lower().endswith(".pdf"):
        raise ValueError(f"Expected a .pdf file, got: {pdf_path}")

    # --- Step 2: Check LM Studio ---
    print(f"[Model] {MODEL}")
    print(f"[Host] {LM_STUDIO_HOST}")
    print()

    if not check_lm_studio_running():
        raise RuntimeError(
            "LM Studio doesn't appear to be running.\n\n"
            "Please:\n"
            "  1. Open LM Studio\n"
            "  2. Load a model (e.g., Qwen, Llama, Mistral)\n"
            "  3. Start the Local Server (bottom-left icon)\n"
            "  4. Try again."
        )

    # --- Step 3: Extract text ---
    print("[Extracting text from PDF...]")
    try:
        text = extract_text(pdf_path)
    except (ImportError, FileNotFoundError) as e:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to extract text: {e}")

    if not text or not text.strip():
        raise ValueError("The PDF contains no extractable text. "
                         "It may be scanned images (try OCR first).")

    text_length = len(text)
    print(f"   Extracted {text_length:,} characters")

    # --- Step 4: Split into chunks ---
    chunks = split_into_chunks(text, CHUNK_SIZE)
    print(f"[Split into {len(chunks)} chunk(s), size: {CHUNK_SIZE}]")
    print()

    # Notify GUI of chunk count
    if progress_callback:
        progress_callback("Chunks ready", 0, len(chunks))

    # --- Step 5: Summarize each chunk ---
    print("[Summarizing chunks...]")
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        status_msg = f"Summarizing chunk {i}/{len(chunks)}"
        print(f"   [{i}/{len(chunks)}] Summarizing chunk ({len(chunk):,} chars)...", end=" ", flush=True)
        if progress_callback:
            progress_callback(status_msg, i, len(chunks))
        try:
            summary = summarize_with_lm_studio(chunk, summary_length=summary_length)
            chunk_summaries.append(summary)
            print("OK")
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            raise

    # --- Step 6: Combine into final summary ---
    print()
    if plain_english:
        print("[Combining into final summary (plain English)...]")
    else:
        print("[Combining into final summary...]")
    if progress_callback:
        progress_callback("Combining summaries", len(chunks), len(chunks))
    final_summary = combine_summaries(chunk_summaries, plain_english=plain_english)

    # --- Step 7: Save ---
    filepath = save_summary(final_summary)
    print(f"[Done] Summary saved to: {filepath}")
    print()

    return filepath


def print_usage() -> None:
    """Print usage instructions."""
    print()
    print("Usage:")
    print("  python pdf_summarizer.py path/to/file.pdf")
    print()
    print("  Or drag and drop a PDF file onto this script.")
    print()
    print("Configuration:")
    print(f"  Edit config.json in the same folder, or set env vars:")
    print(f"    LM_STUDIO_MODEL     - override model name")
    print(f"    LM_STUDIO_HOST      - override LM Studio host")
    print(f"    LM_CHUNK_SIZE       - override chunk size")
    print(f"    LM_TEMPERATURE      - override temperature")
    print(f"    LM_MAX_TOKENS       - override max tokens")
    print()


def main() -> None:
    """Entry point: get PDF path from args or drag-and-drop, then summarize."""
    # Get PDF path from command-line arguments
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # If no args, try to get a file path from the environment
        # (some shells pass dropped files this way)
        if len(sys.argv) == 1 and not sys.stdin.isatty():
            # Check for piped input or file path
            pdf_path = input("Enter PDF file path: ").strip().strip('"\'')
        else:
            pdf_usage = """
No PDF file specified.

Usage:
  python pdf_summarizer.py path/to/your/file.pdf

Or drag and drop a PDF file onto this script.
"""
            print(pdf_usage)
            return

    # Clean up the path (handle quotes, spaces, etc.)
    pdf_path = pdf_path.strip().strip('"\'')

    try:
        filepath = summarize_pdf(pdf_path)
        print("Open the output folder to see your summary.")
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Interrupted by user. Goodbye.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERR] An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
