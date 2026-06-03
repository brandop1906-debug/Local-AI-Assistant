"""
test_api.py
===========
Tests for the FastAPI application routes in app/main.py.

Uses FastAPI's TestClient to verify:
  - /api/chat — chat endpoint (mocked LM Studio)
  - /api/health — health check endpoint
  - /api/chat/history — session CRUD endpoints
  - Error handling (empty messages, missing sessions)
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    """Create a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_ok_when_lm_studio_reachable(self, client):
        """Should return lm_studio: ok when LM Studio responds."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.get", return_value=mock_resp):
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["lm_studio"] == "ok"

    def test_health_returns_unreachable_when_lm_studio_down(self, client):
        """Should return lm_studio: unreachable when LM Studio is down."""
        with patch("requests.get", side_effect=Exception("Connection refused")):
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["lm_studio"] == "unreachable"

    def test_health_returns_unreachable_on_exception(self, client):
        """Should return lm_studio: unreachable when an unexpected exception occurs."""
        with patch("requests.get", side_effect=RuntimeError("Oops")):
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["lm_studio"] == "unreachable"


# ---------------------------------------------------------------------------
# /api/chat
# ---------------------------------------------------------------------------

class TestChatEndpoint:
    def test_chat_with_valid_message(self, client):
        """Should return a response for a valid message."""
        with patch("app.main.ask_ai", return_value="Hello! I'm your AI assistant."):
            response = client.post("/api/chat", json={"text": "Hello"})
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert data["response"] == "Hello! I'm your AI assistant."

    def test_chat_rejects_empty_message(self, client):
        """Should reject empty messages with 400 status."""
        response = client.post("/api/chat", json={"text": ""})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_chat_rejects_whitespace_only(self, client):
        """Should reject whitespace-only messages."""
        response = client.post("/api/chat", json={"text": "   "})
        assert response.status_code == 400

    def test_chat_handles_ask_ai_exception(self, client):
        """Should return error JSON when ask_ai raises an exception."""
        with patch("app.main.ask_ai", side_effect=RuntimeError("LM Studio not responding")):
            response = client.post("/api/chat", json={"text": "Hello"})
            assert response.status_code == 500
            data = response.json()
            assert "error" in data


# ---------------------------------------------------------------------------
# /api/chat/history — session CRUD via API
# ---------------------------------------------------------------------------

class TestChatHistoryAPI:
    def test_create_session(self, client):
        """POST /api/chat/history should create a new session."""
        response = client.post("/api/chat/history", json={"name": "Test Session"})
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert data["session"]["name"] == "Test Session"
        assert "id" in data["session"]

    def test_create_session_default_name(self, client):
        """Should use 'Untitled' as the default session name."""
        response = client.post("/api/chat/history", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["name"] == "Untitled"

    def test_list_sessions(self, client):
        """GET /api/chat/history should return all sessions."""
        # Clear any existing sessions first
        client.post("/api/chat/history/clear")
        # Create sessions via the API
        client.post("/api/chat/history", json={"name": "A"})
        client.post("/api/chat/history", json={"name": "B"})
        response = client.get("/api/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 2

    def test_list_sessions_empty(self, client):
        """Should return empty sessions list when no sessions exist."""
        # Clear any existing sessions first
        client.post("/api/chat/history/clear")
        response = client.get("/api/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    def test_load_session(self, client):
        """GET /api/chat/history/{id} should return the session."""
        create_resp = client.post("/api/chat/history", json={"name": "Load Test"})
        session_id = create_resp.json()["session"]["id"]
        response = client.get(f"/api/chat/history/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["name"] == "Load Test"

    def test_load_missing_session(self, client):
        """Should return 404 for a non-existent session."""
        response = client.get("/api/chat/history/nonexistent")
        assert response.status_code == 404

    def test_rename_session(self, client):
        """PUT /api/chat/history/{id} should rename the session."""
        create_resp = client.post("/api/chat/history", json={"name": "Old Name"})
        session_id = create_resp.json()["session"]["id"]
        response = client.put(
            f"/api/chat/history/{session_id}",
            json={"name": "New Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["name"] == "New Name"

    def test_rename_session_empty_name(self, client):
        """Should reject empty session names."""
        create_resp = client.post("/api/chat/history", json={"name": "Test"})
        session_id = create_resp.json()["session"]["id"]
        response = client.put(
            f"/api/chat/history/{session_id}",
            json={"name": ""},
        )
        assert response.status_code == 400

    def test_rename_missing_session(self, client):
        """Should return 404 when renaming a non-existent session."""
        response = client.put(
            "/api/chat/history/nonexistent",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    def test_delete_session(self, client):
        """DELETE /api/chat/history/{id} should delete the session."""
        create_resp = client.post("/api/chat/history", json={"name": "Delete Me"})
        session_id = create_resp.json()["session"]["id"]
        response = client.delete(f"/api/chat/history/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        # Verify it's gone
        get_resp = client.get(f"/api/chat/history/{session_id}")
        assert get_resp.status_code == 404

    def test_delete_missing_session(self, client):
        """Should return 404 when deleting a non-existent session."""
        response = client.delete("/api/chat/history/nonexistent")
        assert response.status_code == 404

    def test_clear_all_sessions(self, client):
        """POST /api/chat/history/clear should delete all sessions."""
        # Clear first to get a clean slate
        client.post("/api/chat/history/clear")
        client.post("/api/chat/history", json={"name": "A"})
        client.post("/api/chat/history", json={"name": "B"})
        response = client.post("/api/chat/history/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["deleted"] == 2

    def test_chat_with_session(self, client):
        """POST /api/chat/{session_id} should save messages and return response."""
        create_resp = client.post("/api/chat/history", json={"name": "Chat Test"})
        session_id = create_resp.json()["session"]["id"]

        with patch("app.main.ask_ai", return_value="AI response"):
            response = client.post(
                f"/api/chat/{session_id}",
                json={"text": "Hello"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "AI response"
        assert "session_id" in data
        assert data["session_id"] == session_id

    def test_chat_with_session_rejects_empty(self, client):
        """Should reject empty messages in session chat."""
        create_resp = client.post("/api/chat/history", json={"name": "Test"})
        session_id = create_resp.json()["session"]["id"]
        response = client.post(
            f"/api/chat/{session_id}",
            json={"text": ""},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# /api/email
# ---------------------------------------------------------------------------

class TestEmailEndpoint:
    def test_email_rejects_empty_topic(self, client):
        """Should reject empty email topics."""
        response = client.post("/api/email", json={"topic": ""})
        assert response.status_code == 400

    def test_email_with_valid_topic(self, client, tmp_path):
        """Should process a valid email request."""
        import os
        from modules.email_assistant import email_assistant as ea_mod
        output_dir = str(tmp_path / "email_output")
        os.makedirs(output_dir, exist_ok=True)
        with patch.object(ea_mod, "load_template", return_value="Template: {{topic}}"):
            with patch.object(ea_mod, "call_lm_studio", return_value="Dear Sir, ..."):
                with patch.object(ea_mod, "ensure_dir"):
                    with patch.object(ea_mod, "OUTPUT_DIR", output_dir):
                        response = client.post(
                            "/api/email",
                            json={"topic": "Request a meeting", "tone": "professional"},
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "response" in data
                        assert "filepath" in data


# ---------------------------------------------------------------------------
# /api/quote
# ---------------------------------------------------------------------------

class TestQuoteEndpoint:
    def test_quote_with_valid_data(self, client, tmp_path):
        """Should handle quote generation."""
        import os
        from modules.quote_generator import quote_generator as qg_mod
        output_dir = str(tmp_path / "quote_output")
        os.makedirs(output_dir, exist_ok=True)
        with patch.object(qg_mod, "load_template", return_value="Quote template"):
            with patch.object(qg_mod, "call_lm_studio", return_value="Quote content"):
                with patch.object(qg_mod, "ensure_dir"):
                    with patch.object(qg_mod, "OUTPUT_DIR", output_dir):
                        response = client.post(
                            "/api/quote",
                            json={
                                "category": "General Handyman",
                                "customer_name": "John Doe",
                                "services_desc": "Fix the sink",
                                "pricing_items": [],
                            },
                        )
                        assert response.status_code == 200
                        data = response.json()
                        assert "response" in data
                        assert "filepath" in data


# ---------------------------------------------------------------------------
# /api/brain/ask
# ---------------------------------------------------------------------------

class TestBrainAskEndpoint:
    def test_brain_ask_rejects_empty_question(self, client):
        """Should reject empty questions."""
        response = client.post("/api/brain/ask", json={"question": ""})
        assert response.status_code == 400

    def test_brain_ask_with_valid_question(self, client):
        """Should return an answer for a valid question."""
        with patch("business_brain.ask_brain.ask", return_value="The answer is 42."):
            response = client.post("/api/brain/ask", json={"question": "What is the meaning?"})
            assert response.status_code == 200
            data = response.json()
            assert "response" in data

    def test_brain_ask_handles_error(self, client):
        """Should return error JSON when ask_brain raises."""
        with patch("business_brain.ask_brain.ask", side_effect=RuntimeError("Index not found")):
            response = client.post("/api/brain/ask", json={"question": "Hello"})
            assert response.status_code == 500
            data = response.json()
            assert "error" in data


# ---------------------------------------------------------------------------
# /api/brain/reindex
# ---------------------------------------------------------------------------

class TestBrainReindexEndpoint:
    def test_reindex_success(self, client):
        """Should return success status."""
        with patch("app.main.index_documents"):
            response = client.post("/api/brain/reindex")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_reindex_handles_error(self, client):
        """Should return error JSON when reindex fails."""
        with patch("app.main.index_documents", side_effect=RuntimeError("Disk full")):
            response = client.post("/api/brain/reindex")
            assert response.status_code == 500
            data = response.json()
            assert "error" in data


# ---------------------------------------------------------------------------
# /api/pdf/summarize
# ---------------------------------------------------------------------------

class TestPdfSummarizeEndpoint:
    def test_pdf_summarize_rejects_empty_file(self, client):
        """Should reject empty file data."""
        response = client.post("/api/pdf/summarize", json={"file_data": ""})
        assert response.status_code == 400

    def test_pdf_summarize_with_valid_file(self, client, tmp_path):
        """Should process a valid PDF request."""
        import base64
        import os
        # Create a minimal valid PDF base64
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\ntrailer\n<< /Size 3 >>\nstartxref\n0\n%%EOF"
        file_data = base64.b64encode(pdf_content).decode("ascii")

        from modules.pdf_summarizer import pdf_summarizer as ps_mod
        summary_path = str(tmp_path / "summary.txt")
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w") as f:
            f.write("This is a summary.")
        with patch.object(ps_mod, "summarize_pdf", return_value=summary_path):
            response = client.post(
                "/api/pdf/summarize",
                json={"file_data": file_data, "filename": "test.pdf"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
