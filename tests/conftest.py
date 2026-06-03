"""
conftest.py
===========
Shared pytest fixtures for the Local AI Assistant test suite.

Provides:
  - A temporary chat history directory (isolated per test)
  - Mocked LM Studio responses
  - A fixture for creating test sessions
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Temporary chat history directory
# ---------------------------------------------------------------------------

@pytest.fixture()
def chat_history_dir(tmp_path):
    """Provide a temporary directory for chat history storage.

    This fixture replaces the real CHAT_HISTORY_DIR during tests so that
    no real files are modified.  After each test the directory is cleaned
    up automatically by pytest's tmp_path fixture.
    """
    # Point the chat_history module at the temp dir
    import modules.chat_history as chat_history_mod

    original_dir = chat_history_mod.CHAT_HISTORY_DIR
    temp_dir = tmp_path / "chat_history"
    temp_dir.mkdir()
    chat_history_mod.CHAT_HISTORY_DIR = temp_dir
    chat_history_mod._ensure_storage_dir()

    yield temp_dir

    # Restore original
    chat_history_mod.CHAT_HISTORY_DIR = original_dir


# ---------------------------------------------------------------------------
# Mock LM Studio responses
# ---------------------------------------------------------------------------

def _make_chat_response(content: str = "Hello! How can I help you?") -> dict:
    """Create a realistic LM Studio chat completion response."""
    return {
        "model": "qwen:7b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
    }


def _make_embedding_response(embedding: list = None) -> dict:
    """Create a realistic LM Studio embedding response."""
    if embedding is None:
        embedding = [0.1] * 768
    return {
        "model": "nomic-embed-text",
        "data": [{"embedding": embedding}],
    }


@pytest.fixture()
def mock_lm_studio_chat(monkeypatch):
    """Monkeypatch LM Studio chat endpoint to return a fixed response.

    Usage:
        def test_something(mock_lm_studio_chat):
            mock_lm_studio_chat("Custom response")
            # ... code that calls ask_ai() ...
    """
    import subprocess

    def _patch(content="Hello! How can I help you?"):
        response = _make_chat_response(content)
        json_str = json.dumps(response)

        original_run = subprocess.run

        def fake_run(cmd, **kwargs):
            # Check if this is a call to our LM Studio endpoint
            if any("v1/chat/completions" in str(c) for c in cmd):
                result = type("FakeResult", (), {
                    "returncode": 0,
                    "stdout": json_str,
                    "stderr": "",
                })()
                return result
            return original_run(cmd, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        return _FakeChatContext()

    class _FakeChatContext:
        def __call__(self, content="Hello! How can I help you?"):
            response = _make_chat_response(content)
            json_str = json.dumps(response)
            original_run = subprocess.run

            def fake_run(cmd, **kwargs):
                if any("v1/chat/completions" in str(c) for c in cmd):
                    result = type("FakeResult", (), {
                        "returncode": 0,
                        "stdout": json_str,
                        "stderr": "",
                    })()
                    return result
                return original_run(cmd, **kwargs)

            monkeypatch.setattr(subprocess, "run", fake_run)

        def restore(self):
            pass  # monkeypatch handles cleanup automatically

    return _patch()


@pytest.fixture()
def mock_lm_studio_embeddings(monkeypatch):
    """Monkeypatch LM Studio embedding endpoint.

    Usage:
        def test_something(mock_lm_studio_embeddings):
            mock_lm_studio_embeddings([0.1, 0.2, 0.3])
    """
    import urllib.request

    def _patch(embedding=None):
        if embedding is None:
            embedding = [0.1] * 768
        response = _make_embedding_response(embedding)
        json_str = json.dumps(response)

        original_urlopen = urllib.request.urlopen

        def fake_urlopen(req, timeout=None):
            class FakeResponse:
                status = 200
                def read(self):
                    return json_str.encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return FakeResponse()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    return _patch


@pytest.fixture()
def mock_lm_studio_unreachable(monkeypatch):
    """Monkeypatch LM Studio to simulate it being unreachable."""
    import urllib.request

    original_urlopen = urllib.request.urlopen

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    # Also patch subprocess for ask_ai
    import subprocess
    original_run = subprocess.run

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired("cmd", 60)

    monkeypatch.setattr(subprocess, "run", fake_run)


# ---------------------------------------------------------------------------
# Test session helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_session(chat_history_dir):
    """Create and return a fresh test session."""
    from modules.chat_history import new_session
    session = new_session(name="Test Session")
    yield session
    # Cleanup handled by chat_history_dir fixture
