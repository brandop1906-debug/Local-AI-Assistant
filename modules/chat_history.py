"""
chat_history.py
===============
Chat History & Session Management module for the Local AI Assistant.

Stores chat sessions as JSON files in a local directory.
Each session contains:
  - id (UUID)
  - name (auto-derived from first message, user-renamable)
  - created_at / updated_at (ISO timestamps)
  - messages[] (list of {role, content, timestamp})

Usage:
    from chat_history import new_session, save_message, get_sessions, load_session, delete_session
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Storage directory
# ---------------------------------------------------------------------------

_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent
CHAT_HISTORY_DIR = _PROJECT_ROOT / ".local" / "chat_history"


def _ensure_storage_dir():
    """Create the storage directory if it doesn't exist."""
    CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _session_file_path(session_id: str) -> Path:
    """Return the file path for a session."""
    return CHAT_HISTORY_DIR / f"{session_id}.json"


def _iso_now() -> str:
    """Return current time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def new_session(name: str = "Untitled", messages: list = None) -> dict:
    """Create a new chat session and return its data dict."""
    _ensure_storage_dir()
    session_id = str(uuid.uuid4())[:8]
    session = {
        "id": session_id,
        "name": name,
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
        "messages": messages or [],
    }
    # Save to disk
    filepath = _session_file_path(session_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    return session


def get_sessions() -> list:
    """Return all sessions sorted by updated_at (newest first)."""
    _ensure_storage_dir()
    sessions = []
    if not CHAT_HISTORY_DIR.exists():
        return sessions
    for filepath in CHAT_HISTORY_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                session = json.load(f)
            sessions.append(session)
        except (json.JSONDecodeError, OSError):
            continue
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


def load_session(session_id: str) -> dict | None:
    """Load a session by ID. Returns None if not found."""
    filepath = _session_file_path(session_id)
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_message(session_id: str, role: str, content: str) -> dict | None:
    """Append a message to a session and return the updated session."""
    session = load_session(session_id)
    if session is None:
        return None

    session["messages"].append({
        "role": role,
        "content": content,
        "timestamp": _iso_now(),
    })
    session["updated_at"] = _iso_now()

    # Auto-name the session from the first user message
    if session["name"] == "Untitled":
        for msg in session["messages"]:
            if msg["role"] == "user":
                name = msg["content"][:40]
                if len(msg["content"]) > 40:
                    name += "…"
                session["name"] = name
                break

    # Save to disk
    filepath = _session_file_path(session_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    return session


def rename_session(session_id: str, new_name: str) -> dict | None:
    """Rename a session."""
    session = load_session(session_id)
    if session is None:
        return None
    session["name"] = new_name
    session["updated_at"] = _iso_now()
    filepath = _session_file_path(session_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session file. Returns True if deleted, False if not found."""
    filepath = _session_file_path(session_id)
    if filepath.exists():
        filepath.unlink()
        return True
    return False


def get_session_message_count(session_id: str) -> int:
    """Return the number of messages in a session."""
    session = load_session(session_id)
    if session is None:
        return 0
    return len(session["messages"])


def clear_all_sessions() -> int:
    """Delete all session files. Returns count of deleted sessions."""
    _ensure_storage_dir()
    count = 0
    for filepath in CHAT_HISTORY_DIR.glob("*.json"):
        filepath.unlink()
        count += 1
    return count
