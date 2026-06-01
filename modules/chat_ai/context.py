"""
chat_ai/context.py
==================
Project-aware context builder for the Local AI Assistant.

Scans the project directory, reads key documents (pricing, FAQs,
module descriptions, business brain), and builds a concise context
summary that gets injected into every LLM query.

This is what makes the chatbot "know" about your project instead of
answering every question from generic training data.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Resolve paths relative to the project root (parent of chat_ai/)
_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent.parent


# ---------------------------------------------------------------------------
# Document scanners
# ---------------------------------------------------------------------------

def _read_file_safe(filepath: Path) -> Optional[str]:
    """Read a file safely, returning None if it doesn't exist or can't be read."""
    if not filepath.exists():
        return None
    try:
        return filepath.read_text(encoding="utf-8")
    except Exception:
        return None


def _scan_business_brain() -> str:
    """Scan the business_brain documents_dir for indexed knowledge."""
    brain_dir = _PROJECT_ROOT / "business_brain"
    embeddings_file = brain_dir / "embeddings.json"

    if not embeddings_file.exists():
        return ""

    try:
        with open(embeddings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""

    # Extract just the text chunks (skip embeddings — too large)
    chunks = []
    for file_key, file_data in data.items():
        chunks_in_file = file_data.get("chunks", [])
        for chunk in chunks_in_file:
            text = chunk.get("text", "")
            if text and len(text) > 50:  # skip tiny chunks
                chunks.append(text[:2000])  # cap each chunk

    return "\n\n---\n\n".join(chunks[:20])  # limit to top 20 chunks


def _scan_config_files() -> str:
    """Read key configuration files for project metadata."""
    sections = []

    # Launcher config (modules list)
    launcher_config = _PROJECT_ROOT / "config.json"
    if launcher_config.exists():
        try:
            with open(launcher_config, "r", encoding="utf-8") as f:
                config = json.load(f)
            modules = config.get("modules", [])
            if modules:
                module_list = "\n".join(
                    f"  - {m['name']}: {m['path']}" for m in modules
                )
                sections.append(f"## Configured Modules\n{module_list}")
        except Exception:
            pass

    # Chat AI config
    chat_config = _MODULE_DIR / "config.json"
    if chat_config.exists():
        try:
            with open(chat_config, "r", encoding="utf-8") as f:
                chat_cfg = json.load(f)
            sections.append(
                f"## Chat AI Config\n"
                f"- Model: {chat_cfg.get('model', 'N/A')}\n"
                f"- Temperature: {chat_cfg.get('temperature', 'N/A')}\n"
                f"- Max Tokens: {chat_cfg.get('max_tokens', 'N/A')}"
            )
        except Exception:
            pass

    return "\n\n".join(sections)


def _scan_documents_dir() -> str:
    """Scan business_brain/documents for text/PDF/DOCX files."""
    docs_dir = _PROJECT_ROOT / "business_brain" / "documents"
    if not docs_dir.exists():
        return ""

    sections = []
    for root, dirs, files in os.walk(docs_dir):
        for filename in files:
            if filename.endswith((".txt", ".md", ".json")):
                filepath = Path(root) / filename
                content = _read_file_safe(filepath)
                if content:
                    sections.append(f"## {filepath.relative_to(docs_dir)}\n{content[:3000]}")

    return "\n\n---\n\n".join(sections)


def _scan_readme_files() -> str:
    """Find and read any README files in the project."""
    readmes = []
    for readme in _PROJECT_ROOT.glob("**/README*"):
        if readme.is_file():
            content = _read_file_safe(readme)
            if content:
                readmes.append(f"## {readme.relative_to(_PROJECT_ROOT)}\n{content[:2000]}")
    return "\n\n---\n\n".join(readmes)


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_project_context(max_tokens: int = 8000) -> str:
    """
    Build a comprehensive context string from all project sources.

    This is injected into the LLM's system prompt so it "knows" about:
    - The project's purpose and structure
    - All configured modules
    - Business documents and FAQs
    - Pricing information (if available)
    - README and documentation

    Args:
        max_tokens: Maximum approximate token count for the context.
                    Default: 8000 (~32KB). Smaller values prioritize
                    the most important documents.

    Returns:
        str: A formatted context string ready for insertion into the
             system prompt.
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

    # Add modules from config
    launcher_config = _PROJECT_ROOT / "config.json"
    if launcher_config.exists():
        try:
            with open(launcher_config, "r", encoding="utf-8") as f:
                config = json.load(f)
            for mod in config.get("modules", []):
                parts.append(f"- **{mod['name']}**: {mod['path']}")
        except Exception:
            pass

    # Estimate remaining budget
    used = len("\n".join(parts).split())
    budget = max_tokens - used

    if budget > 500:
        parts.append("\n## Business Knowledge Base")

        # Add business brain content (priority)
        brain_content = _scan_business_brain()
        if brain_content:
            parts.append(brain_content)
            used += len(brain_content.split())
            budget = max_tokens - used

        # Add documents directory content (if budget allows)
        if budget > 1000:
            docs_content = _scan_documents_dir()
            if docs_content:
                parts.append("\n## Additional Documents")
                parts.append(docs_content)
                used += len(docs_content.split())
                budget = max_tokens - used

        # Add READMEs (if budget allows)
        if budget > 500:
            readme_content = _scan_readme_files()
            if readme_content:
                parts.append("\n## Project Documentation")
                parts.append(readme_content)

    elif budget > 0:
        # Not enough budget for business brain — add a note
        parts.append(
            "(Context budget exhausted. Business documents are indexed in"
            " business_brain/documents/ — add files there and re-index.)"
        )

    parts.append("\n=== END CONTEXT ===")

    return "\n".join(parts)


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
