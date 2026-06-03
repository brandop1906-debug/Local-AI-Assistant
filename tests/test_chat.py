"""
test_chat.py
============
Tests for the chat_ai/chat module.

Covers:
  - _load_config (config validation)
  - _build_api_url
  - _build_payload
  - ask_ai (with mocked subprocess)
"""

import json

import pytest
import requests

from modules.chat_ai import chat


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_valid_config(self):
        """Should load the existing config.json successfully."""
        config = chat._load_config()
        assert "system_prompt" in config
        assert "temperature" in config
        assert "max_tokens" in config

    def test_missing_config_file(self, monkeypatch):
        """Should raise FileNotFoundError when config is missing."""
        import os
        original_exists = os.path.exists

        def fake_exists(path):
            if "config.json" in str(path):
                return False
            return original_exists(path)

        monkeypatch.setattr(os.path, "exists", fake_exists)
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            chat._load_config()

    def test_missing_required_key(self, tmp_path, monkeypatch):
        """Should raise ValueError when a required key is missing."""
        config_path = tmp_path / "chat_ai" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump({"temperature": 0.7}, f)  # missing system_prompt, max_tokens

        original_file = chat._CONFIG_FILE
        chat._CONFIG_FILE = config_path
        try:
            with pytest.raises(ValueError, match="Missing required config key"):
                chat._load_config()
        finally:
            chat._CONFIG_FILE = original_file


# ---------------------------------------------------------------------------
# _build_api_url
# ---------------------------------------------------------------------------

class TestBuildApiUrl:
    def test_default_url(self):
        """Should return the default URL when not overridden."""
        config = {}
        result = chat._build_api_url(config)
        assert result == "http://localhost:1234/v1/chat/completions"

    def test_custom_url(self):
        """Should use the custom URL from config."""
        config = {"api_url": "http://custom:8080/v1/chat/completions"}
        result = chat._build_api_url(config)
        assert result == "http://custom:8080/v1/chat/completions"


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_basic_payload(self):
        """Should build a valid payload with defaults."""
        config = {
            "system_prompt": "You are a helpful assistant.",
            "temperature": 0.7,
            "max_tokens": 2048,
            "model": "qwen:7b",
        }
        payload = chat._build_payload("Hello", config)
        assert payload["model"] == "qwen:7b"
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 2048
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "Hello"

    def test_custom_system_message(self):
        """Should use the provided system message."""
        config = {"system_prompt": "Default system"}
        payload = chat._build_payload("Hello", config, system_message="Custom system")
        assert payload["messages"][0]["content"] == "Custom system"

    def test_payload_is_json_serializable(self):
        """The payload should be valid JSON."""
        config = {
            "system_prompt": "Test",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        payload = chat._build_payload("Hello", config)
        json_str = json.dumps(payload)
        # Should not raise
        loaded = json.loads(json_str)
        assert loaded == payload


# ---------------------------------------------------------------------------
# ask_ai
# ---------------------------------------------------------------------------

def _mock_response(data: dict, status_code: int = 200):
    """Build a minimal mock requests.Response."""
    body = json.dumps(data)
    resp = type("MockResponse", (), {
        "status_code": status_code,
        "text": body,
        "json": lambda self: data,
        "raise_for_status": lambda self: None,
    })()
    return resp


class TestAskAi:
    def test_returns_response_on_success(self, monkeypatch):
        """Should return the AI response on a successful call."""
        mock_data = {
            "model": "qwen:7b",
            "choices": [{"message": {"content": "Hello! How can I help?"}}],
        }
        monkeypatch.setattr(requests, "post", lambda *a, **kw: _mock_response(mock_data))
        result = chat.ask_ai("Hello")
        assert result == "Hello! How can I help?"

    def test_raises_on_timeout(self, monkeypatch):
        """Should raise RuntimeError on API timeout."""
        def raise_timeout(*args, **kwargs):
            raise requests.exceptions.Timeout()
        monkeypatch.setattr(requests, "post", raise_timeout)
        with pytest.raises(RuntimeError, match="API call timed out"):
            chat.ask_ai("Hello")

    def test_raises_on_connection_error(self, monkeypatch):
        """Should raise RuntimeError when LM Studio is unreachable."""
        def raise_conn(*args, **kwargs):
            raise requests.exceptions.ConnectionError("Connection refused")
        monkeypatch.setattr(requests, "post", raise_conn)
        with pytest.raises(RuntimeError, match="Cannot connect to LM Studio"):
            chat.ask_ai("Hello")

    def test_raises_on_invalid_json(self, monkeypatch):
        """Should raise RuntimeError on invalid JSON response."""
        resp = type("MockResponse", (), {
            "status_code": 200,
            "text": "not json at all",
            "json": lambda self: (_ for _ in ()).throw(ValueError("No JSON")),
            "raise_for_status": lambda self: None,
        })()
        monkeypatch.setattr(requests, "post", lambda *a, **kw: resp)
        with pytest.raises(RuntimeError, match="invalid JSON"):
            chat.ask_ai("Hello")

    def test_raises_on_missing_choices(self, monkeypatch):
        """Should raise RuntimeError when choices is missing."""
        mock_data = {"model": "qwen:7b"}  # no "choices" key
        monkeypatch.setattr(requests, "post", lambda *a, **kw: _mock_response(mock_data))
        with pytest.raises(RuntimeError, match="Unexpected response format"):
            chat.ask_ai("Hello")

    def test_raises_on_empty_choices(self, monkeypatch):
        """Should raise RuntimeError when choices is empty."""
        mock_data = {"choices": []}
        monkeypatch.setattr(requests, "post", lambda *a, **kw: _mock_response(mock_data))
        with pytest.raises(RuntimeError, match="no choices"):
            chat.ask_ai("Hello")

    def test_ask_ai_with_include_context_false(self, monkeypatch):
        """Should work without RAG context when include_context=False."""
        mock_data = {
            "model": "qwen:7b",
            "choices": [{"message": {"content": "Simple response"}}],
        }
        monkeypatch.setattr(requests, "post", lambda *a, **kw: _mock_response(mock_data))
        result = chat.ask_ai("Hello", include_context=False)
        assert result == "Simple response"
