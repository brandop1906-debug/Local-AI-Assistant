"""
test_chat_history.py
====================
Tests for the chat_history module (session CRUD operations).

Covers:
  - Creating new sessions
  - Listing sessions
  - Loading individual sessions
  - Saving messages to sessions
  - Renaming sessions
  - Deleting sessions
  - Clearing all sessions
  - Edge cases (missing files, malformed JSON)
"""

import json
from pathlib import Path

import pytest

from modules import chat_history


# ---------------------------------------------------------------------------
# new_session
# ---------------------------------------------------------------------------

class TestNewSession:
    def test_creates_session_with_defaults(self, chat_history_dir):
        """A new session should have sensible defaults."""
        session = chat_history.new_session()
        assert session["name"] == "Untitled"
        assert "id" in session
        assert len(session["id"]) == 8  # truncated UUID
        assert session["messages"] == []
        assert "created_at" in session
        assert "updated_at" in session
        # File should exist on disk
        assert chat_history_dir.exists()
        files = list(chat_history_dir.glob("*.json"))
        assert len(files) == 1

    def test_creates_session_with_custom_name(self, chat_history_dir):
        """A session should be created with a custom name."""
        session = chat_history.new_session(name="My Chat")
        assert session["name"] == "My Chat"

    def test_session_file_is_valid_json(self, chat_history_dir):
        """The session file should be valid JSON."""
        chat_history.new_session(name="JSON Test")
        files = list(chat_history_dir.glob("*.json"))
        assert len(files) == 1
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "JSON Test"

    def test_multiple_sessions_create_separate_files(self, chat_history_dir):
        """Each session should create its own file."""
        s1 = chat_history.new_session(name="First")
        s2 = chat_history.new_session(name="Second")
        assert s1["id"] != s2["id"]
        files = list(chat_history_dir.glob("*.json"))
        assert len(files) == 2

    def test_session_id_is_unique(self, chat_history_dir):
        """Session IDs should be unique across calls."""
        ids = {chat_history.new_session()["id"] for _ in range(10)}
        assert len(ids) == 10


# ---------------------------------------------------------------------------
# get_sessions
# ---------------------------------------------------------------------------

class TestGetSessions:
    def test_returns_empty_list_when_no_sessions(self, chat_history_dir):
        """Should return an empty list when no sessions exist."""
        sessions = chat_history.get_sessions()
        assert sessions == []

    def test_returns_all_sessions(self, chat_history_dir):
        """Should return all sessions."""
        chat_history.new_session(name="A")
        chat_history.new_session(name="B")
        chat_history.new_session(name="C")
        sessions = chat_history.get_sessions()
        assert len(sessions) == 3

    def test_sessions_sorted_by_updated_at_newest_first(self, chat_history_dir):
        """Sessions should be sorted by updated_at descending."""
        s1 = chat_history.new_session(name="First")
        import time
        time.sleep(0.01)
        s2 = chat_history.new_session(name="Second")

        sessions = chat_history.get_sessions()
        assert sessions[0]["id"] == s2["id"]
        assert sessions[1]["id"] == s1["id"]

    def test_skips_malformed_json(self, chat_history_dir):
        """get_sessions should skip files with invalid JSON."""
        chat_history.new_session(name="Good")
        # Write a malformed JSON file
        bad_file = chat_history_dir / "bad_session.json"
        bad_file.write_text("{invalid json}}}")
        sessions = chat_history.get_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "Good"

    def test_skips_non_json_files(self, chat_history_dir):
        """get_sessions should ignore non-JSON files."""
        chat_history.new_session(name="Real")
        (chat_history_dir / "notes.txt").write_text("not a session")
        sessions = chat_history.get_sessions()
        assert len(sessions) == 1


# ---------------------------------------------------------------------------
# load_session
# ---------------------------------------------------------------------------

class TestLoadSession:
    def test_loads_existing_session(self, chat_history_dir):
        """Should return the session data for a valid ID."""
        session = chat_history.new_session(name="Load Test")
        loaded = chat_history.load_session(session["id"])
        assert loaded is not None
        assert loaded["name"] == "Load Test"
        assert loaded["id"] == session["id"]

    def test_returns_none_for_missing_session(self, chat_history_dir):
        """Should return None for a non-existent session ID."""
        result = chat_history.load_session("nonexistent")
        assert result is None

    def test_returns_none_for_malformed_file(self, chat_history_dir):
        """Should return None for a session file with invalid JSON."""
        # Create a file with the right naming pattern but bad content
        bad_file = chat_history_dir / "deadbeef.json"
        bad_file.write_text("{bad json!")
        result = chat_history.load_session("deadbeef")
        assert result is None

    def test_session_content_matches(self, chat_history_dir):
        """Loaded session should match the original."""
        original = chat_history.new_session(name="Content Test", messages=[
            {"role": "user", "content": "Hello"},
            {"role": "ai", "content": "Hi there!"},
        ])
        loaded = chat_history.load_session(original["id"])
        assert loaded["messages"] == original["messages"]


# ---------------------------------------------------------------------------
# save_message
# ---------------------------------------------------------------------------

class TestSaveMessage:
    def test_appends_user_message(self, chat_history_dir):
        """Should append a user message to the session."""
        session = chat_history.new_session(name="Message Test")
        result = chat_history.save_message(session["id"], "user", "Hello")
        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        assert "timestamp" in result["messages"][0]

    def test_appends_ai_message(self, chat_history_dir):
        """Should append an AI message to the session."""
        session = chat_history.new_session(name="AI Message")
        chat_history.save_message(session["id"], "user", "Hi")
        result = chat_history.save_message(session["id"], "ai", "Hello!")
        assert result["messages"][-1]["role"] == "ai"

    def test_updates_updated_at_on_save(self, chat_history_dir):
        """Saving a message should update the updated_at timestamp."""
        session = chat_history.new_session(name="Timestamp Test")
        original_updated = session["updated_at"]
        import time
        time.sleep(0.01)
        chat_history.save_message(session["id"], "user", "New message")
        loaded = chat_history.load_session(session["id"])
        assert loaded["updated_at"] != original_updated

    def test_autonames_untitled_sessions(self, chat_history_dir):
        """An 'Untitled' session should be auto-named from the first user message."""
        session = chat_history.new_session(name="Untitled")
        chat_history.save_message(session["id"], "user", "Hello, how are you today?")
        loaded = chat_history.load_session(session["id"])
        assert loaded["name"] == "Hello, how are you today?"

    def test_autonames_truncates_long_messages(self, chat_history_dir):
        """Auto-name should truncate messages longer than 40 chars."""
        session = chat_history.new_session(name="Untitled")
        long_msg = "A" * 100
        chat_history.save_message(session["id"], "user", long_msg)
        loaded = chat_history.load_session(session["id"])
        assert len(loaded["name"]) <= 41  # 40 chars + ellipsis

    def test_returns_none_for_missing_session(self, chat_history_dir):
        """save_message should return None for a non-existent session."""
        result = chat_history.save_message("nonexistent", "user", "Hello")
        assert result is None

    def test_messages_persist_across_loads(self, chat_history_dir):
        """Messages should persist when the session is reloaded."""
        session = chat_history.new_session(name="Persistence")
        chat_history.save_message(session["id"], "user", "Msg 1")
        chat_history.save_message(session["id"], "ai", "Reply 1")
        chat_history.save_message(session["id"], "user", "Msg 2")
        loaded = chat_history.load_session(session["id"])
        assert len(loaded["messages"]) == 3
        assert loaded["messages"][0]["content"] == "Msg 1"
        assert loaded["messages"][1]["content"] == "Reply 1"
        assert loaded["messages"][2]["content"] == "Msg 2"


# ---------------------------------------------------------------------------
# rename_session
# ---------------------------------------------------------------------------

class TestRenameSession:
    def test_renames_session(self, chat_history_dir):
        """Should update the session name."""
        session = chat_history.new_session(name="Old Name")
        result = chat_history.rename_session(session["id"], "New Name")
        assert result["name"] == "New Name"
        loaded = chat_history.load_session(session["id"])
        assert loaded["name"] == "New Name"

    def test_returns_none_for_missing_session(self, chat_history_dir):
        """Should return None for a non-existent session."""
        result = chat_history.rename_session("nonexistent", "New Name")
        assert result is None

    def test_updates_updated_at_on_rename(self, chat_history_dir):
        """Renaming should update the updated_at timestamp."""
        session = chat_history.new_session(name="Rename Test")
        original_updated = session["updated_at"]
        import time
        time.sleep(0.01)
        chat_history.rename_session(session["id"], "Renamed")
        loaded = chat_history.load_session(session["id"])
        assert loaded["updated_at"] != original_updated


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------

class TestDeleteSession:
    def test_deletes_session_file(self, chat_history_dir):
        """Should delete the session file."""
        session = chat_history.new_session(name="To Delete")
        result = chat_history.delete_session(session["id"])
        assert result is True
        assert chat_history.load_session(session["id"]) is None

    def test_returns_false_for_missing_session(self, chat_history_dir):
        """Should return False for a non-existent session."""
        result = chat_history.delete_session("nonexistent")
        assert result is False

    def test_file_removed_from_disk(self, chat_history_dir):
        """The session file should be physically removed."""
        session = chat_history.new_session(name="File Test")
        chat_history.delete_session(session["id"])
        files = list(chat_history_dir.glob("*.json"))
        assert len(files) == 0


# ---------------------------------------------------------------------------
# clear_all_sessions
# ---------------------------------------------------------------------------

class TestClearAllSessions:
    def test_clears_all_sessions(self, chat_history_dir):
        """Should delete all session files."""
        chat_history.new_session(name="A")
        chat_history.new_session(name="B")
        chat_history.new_session(name="C")
        count = chat_history.clear_all_sessions()
        assert count == 3
        sessions = chat_history.get_sessions()
        assert sessions == []

    def test_returns_zero_when_no_sessions(self, chat_history_dir):
        """Should return 0 when there are no sessions."""
        count = chat_history.clear_all_sessions()
        assert count == 0

    def test_does_not_delete_non_json_files(self, chat_history_dir):
        """clear_all_sessions should only delete .json files."""
        chat_history.new_session(name="Real")
        (chat_history_dir / "notes.txt").write_text("keep me")
        chat_history.clear_all_sessions()
        assert (chat_history_dir / "notes.txt").exists()


# ---------------------------------------------------------------------------
# get_session_message_count
# ---------------------------------------------------------------------------

class TestGetSessionMessageCount:
    def test_returns_message_count(self, chat_history_dir):
        """Should return the correct number of messages."""
        session = chat_history.new_session(name="Count Test")
        assert chat_history.get_session_message_count(session["id"]) == 0
        chat_history.save_message(session["id"], "user", "Hello")
        chat_history.save_message(session["id"], "ai", "Hi!")
        assert chat_history.get_session_message_count(session["id"]) == 2

    def test_returns_zero_for_missing_session(self, chat_history_dir):
        """Should return 0 for a non-existent session."""
        assert chat_history.get_session_message_count("nonexistent") == 0
