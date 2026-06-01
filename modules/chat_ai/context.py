"""
chat_ai/context.py
==================
Project-aware context builder for the Local AI Assistant.

Now uses RAG (Retrieval-Augmented Generation) to dynamically retrieve
only the most relevant document chunks for each query, instead of
dumping all documents into the system prompt.

This is far more efficient and scalable.

Usage:
    from chat_ai.context import build_rag_context, inject_context
    context = build_rag_context("What is the pricing structure?", top_k=5)
    system_prompt = inject_context(base_prompt, context)
"""

import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MODULE_DIR = Path(__file__).resolve().parent
# chat_ai is inside modules/, go up TWO levels to reach project root
_PROJECT_ROOT = _MODULE_DIR.parent.parent


# ---------------------------------------------------------------------------
# Legacy compatibility: build_project_context() kept as a thin wrapper
# that now delegates to the RAG-aware builder.
# ---------------------------------------------------------------------------

def build_project_context(max_tokens: int = 8000) -> str:
    """
    Build a project context string.

    NOTE: This is kept for backward compatibility. For query-aware context,
    use build_rag_context(query, top_k) instead, which uses RAG to retrieve
    only the most relevant chunks.

    Args:
        max_tokens: Maximum approximate token count (unused in RAG mode).

    Returns:
        str: A context string with project metadata + module list.
    """
    parts = [
        "=== PROJECT CONTEXT ===",
        "",
        "## Project Overview",
        "Local AI Assistant is a desktop application that provides AI-powered",
        "tools for business automation. All processing happens locally on the",
        "user's machine — no cloud APIs, no data leaves the device.",
        "",
        "## Configured Modules",
        "The following modules are available in the launcher:",
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

    parts.append("\n=== END CONTEXT ===")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# RAG-aware context builder (imported from rag.py)
# ---------------------------------------------------------------------------
from chat_ai.rag import build_rag_context  # noqa: E402


# ---------------------------------------------------------------------------
# Context injector
# ---------------------------------------------------------------------------

def inject_context(system_prompt: str, context: Optional[str] = None) -> str:
    """
    Inject project context into the system prompt.

    Args:
        system_prompt: The original system prompt from config.json.
        context: Pre-built context string (if None, build_project_context() is called).

    Returns:
        str: The combined system prompt with context included.
    """
    if context is None:
        context = build_project_context()

    # Insert context between the system prompt and a reference to it
    return (
        f"{system_prompt}\n\n"
        f"---\n\n"
        f"Here is additional context about this project. Use this information "
        f"to answer questions about the project, its modules, pricing, and "
        f"business operations:\n\n"
        f"{context}"
    )
