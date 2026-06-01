"""
chat_ai/chat.py
===============
Local LLM chat module for the Local AI Assistant.

Communicates with LM Studio's local API server (OpenAI-compatible)
to send messages and receive responses — no cloud APIs required.

Uses RAG (Retrieval-Augmented Generation) to dynamically retrieve only
the most relevant document chunks for each query, instead of dumping
all documents into the prompt. This makes the chatbot "know" about
your project efficiently and scalably.

Usage:
    from chat_ai.chat import ask_ai
    response = ask_ai("What is the pricing structure?")
    print(response)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure the parent directory (modules/) is on sys.path so imports work
# regardless of whether we're launched from the project root or modules/
_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR.parent))

# Import the context builder (same directory)
from chat_ai.context import build_rag_context, inject_context

# ---------------------------------------------------------------------------
# Configuration paths
# ---------------------------------------------------------------------------
_MODULE_DIR = Path(__file__).resolve().parent
_CONFIG_FILE = _MODULE_DIR / "config.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load and return the configuration from config.json.

    Returns:
        dict: Parsed JSON configuration.

    Raises:
        FileNotFoundError: If config.json does not exist.
        json.JSONDecodeError: If config.json is malformed.
    """
    if not _CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file not found: {_CONFIG_FILE}\n"
            "Please ensure config.json exists in the chat_ai/ directory."
        )

    with open(_CONFIG_FILE, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    # Validate required keys
    required_keys = ["system_prompt", "temperature", "max_tokens"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: '{key}'")

    return config


def _build_api_url(config: dict) -> str:
    """Build the full API endpoint URL.

    The 'api_url' key in config.json can override the default.
    Default: http://localhost:1234/v1/chat/completions
    """
    default_url = "http://localhost:1234/v1/chat/completions"
    return config.get("api_url", default_url)


def _build_payload(
    user_message: str,
    config: dict,
    system_message: str | None = None,
) -> dict:
    """Build the JSON payload for the LM Studio API call.

    Args:
        user_message: The user's input text.
        config: Loaded configuration dictionary.
        system_message: Optional system message. If None, uses the
                        system_prompt from config.json.

    Returns:
        dict: The request payload ready to be JSON-serialized.
    """
    sys_msg = system_message or config["system_prompt"]

    return {
        "model": config.get("model", "qwen:7b"),
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_message},
        ],
        "temperature": config.get("temperature", 0.7),
        "max_tokens": config.get("max_tokens", 2048),
        "stream": False,
    }


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def ask_ai(user_message: str, include_context: bool = True) -> str:
    """Send a user message to the local LM Studio model and return the response.

    This function:
        1. Loads config.json from the chat_ai/ directory.
        2. Builds project context (business docs, modules, pricing, FAQs).
        3. Injects context into the system prompt.
        4. Sends the request to LM Studio's local server via subprocess (curl).
        5. Parses and returns the model's text response.

    Args:
        user_message (str): The text input from the user.
        include_context (bool): If True, injects project context into the
                                system prompt. Default: True.

    Returns:
        str: The model's response as a plain string.

    Raises:
        FileNotFoundError: If config.json is missing.
        json.JSONDecodeError: If config.json is invalid.
        RuntimeError: If LM Studio is unreachable or returns an error.
        subprocess.TimeoutExpired: If the API call times out.
    """
    # Step 1 — Load configuration
    config = _load_config()

    # Step 2 — Build and inject project context (if enabled)
    if include_context:
        # Use RAG-aware context: only retrieve the most relevant chunks
        # for this specific query, instead of dumping all documents
        context = build_rag_context(user_message, top_k=5, max_context_chars=6000)
        system_message = inject_context(config["system_prompt"], context)
    else:
        system_message = None

    # Step 3 — Build the API URL and payload
    api_url = _build_api_url(config)
    payload = _build_payload(user_message, config, system_message)

    # Step 3 — Send the request using subprocess + curl
    # We use curl because it is available on Windows by default (Win10+)
    # and avoids needing the `requests` library as an extra dependency.
    try:
        # Build the curl command as a list (safer than shell=True)
        cmd = [
            "curl",
            "-X", "POST",
            api_url,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            "--max-time", "60",          # 60-second timeout
            "-s",                         # silent mode (no progress bar)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",           # force UTF-8 — curl returns UTF-8
            timeout=65,                 # slightly longer than curl's internal timeout
        )

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            "API call timed out. Is LM Studio running and is the model loaded? "
            f"Expected server at {api_url}"
        )
    except FileNotFoundError:
        raise RuntimeError(
            "curl not found. Please ensure curl is installed on your system "
            "(it ships with Windows 10/11 by default)."
        )

    # Step 4 — Check for curl-level errors (non-zero exit code)
    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else "(no output)"
        raise RuntimeError(
            f"curl failed (exit code {result.returncode}): {stderr}\n"
            f"Is LM Studio running? Is the correct model loaded? "
            f"Server URL: {api_url}"
        )

    # Step 5 — Parse the JSON response from LM Studio
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("LM Studio returned an empty response.")

    try:
        response_data = json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"LM Studio returned invalid JSON:\n{stdout[:500]}"
        )

    # Step 6 — Extract the text content from the response
    try:
        choices = response_data["choices"]
        if not choices:
            raise RuntimeError("LM Studio returned no choices in the response.")
        content = choices[0]["message"]["content"]
    except KeyError as exc:
        raise RuntimeError(
            f"Unexpected response format from LM Studio:\n{stdout[:500]}\n"
            f"Missing key: {exc}"
        )

    return content


# ---------------------------------------------------------------------------
# Quick CLI test (run with: python chat.py "Hello!")
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test ask_ai() by sending a message via the CLI."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="Hello, who are you?",
        help='The message to send to the local LLM (default: "Hello, who are you?")',
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Local AI Assistant — ask_ai() CLI test")
    print("=" * 60)
    print(f"\n[You]   {args.message}")
    print("-" * 60)

    try:
        response = ask_ai(args.message)
        print(f"[AI]    {response}")
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print("-" * 60)
    print("Done.\n")
