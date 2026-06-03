"""
test_ask_brain.py
=================
Tests for the business_brain/ask_brain module.

Covers:
  - keyword_search
  - load_index
  - get_lm_studio_url / get_embedding_model / get_llm_model
  - generate_answer
  - ask (main entry point)
"""

import json
import os
import tempfile

import pytest

from business_brain import ask_brain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_index(num_files=2, chunks_per_file=3):
    """Create a minimal embeddings index dict for testing."""
    index = {}
    for i in range(num_files):
        relpath = f"doc_{i}.txt"
        chunks = []
        for j in range(chunks_per_file):
            chunks.append({
                "chunk_index": j,
                "text": f"This is chunk {j} of document {i}. It contains relevant information.",
                "embedding": [0.1] * 10,
            })
        index[relpath] = {
            "file_path": f"/tmp/{relpath}",
            "file_hash": f"hash_{i}",
            "chunks": chunks,
        }
    return index


def _write_temp_index(index_dict, tmp_path):
    """Write an index dict to a temp file and return the path."""
    path = os.path.join(tmp_path, "embeddings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index_dict, f)
    return path


# ---------------------------------------------------------------------------
# load_index
# ---------------------------------------------------------------------------

class TestLoadIndex:
    def test_loads_valid_index(self, tmp_path):
        """Should load a valid index file."""
        index = _make_index()
        path = _write_temp_index(index, tmp_path)
        loaded = ask_brain.load_index(path)
        assert "doc_0.txt" in loaded
        assert "doc_1.txt" in loaded

    def test_load_index_exits_on_missing_file(self, tmp_path):
        """Should call sys.exit(1) when the index file is missing."""
        missing_path = os.path.join(str(tmp_path), "nonexistent.json")
        with pytest.raises(SystemExit):
            ask_brain.load_index(missing_path)


# ---------------------------------------------------------------------------
# keyword_search
# ---------------------------------------------------------------------------

class TestKeywordSearch:
    def test_finds_matching_chunks(self):
        """Should return chunks containing the query term."""
        index = _make_index()
        results = ask_brain.keyword_search("document 0", index, top_k=5)
        assert len(results) > 0
        assert results[0]["file"] == "doc_0.txt"

    def test_returns_empty_for_no_match(self):
        """Should return empty list when nothing matches."""
        index = _make_index()
        results = ask_brain.keyword_search("xyznonexistent", index)
        assert results == []

    def test_respects_top_k(self):
        """Should limit results to top_k."""
        index = _make_index(num_files=10, chunks_per_file=10)
        results = ask_brain.keyword_search("document", index, top_k=3)
        assert len(results) <= 3

    def test_case_insensitive(self):
        """Search should be case-insensitive."""
        index = _make_index()
        results_upper = ask_brain.keyword_search("DOCUMENT 0", index)
        results_lower = ask_brain.keyword_search("document 0", index)
        assert len(results_upper) == len(results_lower)

    def test_scores_by_frequency(self):
        """Higher frequency matches should score higher."""
        index = _make_index()
        results = ask_brain.keyword_search("document", index)
        # Results should be sorted by score descending
        for i in range(len(results) - 1):
            assert results[i]["score"] >= results[i + 1]["score"]


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

class TestConfigHelpers:
    def test_get_lm_studio_url_default(self, tmp_path):
        """Should return default URL when config is missing."""
        # The function hardcodes the path to config.json in its own directory
        # Create a temp copy of the directory with a missing config
        import shutil
        src_dir = os.path.dirname(os.path.abspath(ask_brain.__file__))
        dst_dir = os.path.join(str(tmp_path), "business_brain")
        os.makedirs(dst_dir, exist_ok=True)
        # Copy all files except config.json
        for fname in os.listdir(src_dir):
            if fname != "config.json":
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        # Now patch __file__ temporarily
        original_file = ask_brain.__file__
        ask_brain.__file__ = os.path.join(dst_dir, "ask_brain.py")
        try:
            result = ask_brain.get_lm_studio_url()
            assert result == "http://localhost:1234"
        finally:
            ask_brain.__file__ = original_file

    def test_get_embedding_model_default(self, tmp_path):
        """Should return default embedding model."""
        import shutil
        src_dir = os.path.dirname(os.path.abspath(ask_brain.__file__))
        dst_dir = os.path.join(str(tmp_path), "business_brain")
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            if fname != "config.json":
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        original_file = ask_brain.__file__
        ask_brain.__file__ = os.path.join(dst_dir, "ask_brain.py")
        try:
            result = ask_brain.get_embedding_model()
            assert result == "nomic-embed-text"
        finally:
            ask_brain.__file__ = original_file

    def test_get_llm_model_default(self, tmp_path):
        """Should return default LLM model."""
        import shutil
        src_dir = os.path.dirname(os.path.abspath(ask_brain.__file__))
        dst_dir = os.path.join(str(tmp_path), "business_brain")
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            if fname != "config.json":
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        original_file = ask_brain.__file__
        ask_brain.__file__ = os.path.join(dst_dir, "ask_brain.py")
        try:
            result = ask_brain.get_llm_model()
            assert result == "local-model"
        finally:
            ask_brain.__file__ = original_file

    def test_get_lm_studio_chat_url_default(self, tmp_path):
        """Should return None when chat URL is not configured."""
        import shutil
        src_dir = os.path.dirname(os.path.abspath(ask_brain.__file__))
        dst_dir = os.path.join(str(tmp_path), "business_brain")
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            if fname != "config.json":
                src = os.path.join(src_dir, fname)
                dst = os.path.join(dst_dir, fname)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

        original_file = ask_brain.__file__
        ask_brain.__file__ = os.path.join(dst_dir, "ask_brain.py")
        try:
            result = ask_brain.get_lm_studio_chat_url()
            assert result is None
        finally:
            ask_brain.__file__ = original_file


# ---------------------------------------------------------------------------
# generate_answer
# ---------------------------------------------------------------------------

class TestGenerateAnswer:
    def test_generates_answer_with_lm_studio(self, monkeypatch):
        """Should send context to LM Studio and return the answer."""
        context_chunks = [
            {"text": "Relevant info about the topic."},
            {"text": "Additional details."},
        ]
        mock_response = {"choices": [{"message": {"content": "The answer is 42."}}]}

        def mock_urlopen(req, timeout=None):
            class FakeResp:
                status = 200
                def read(self):
                    return json.dumps(mock_response).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    pass
            return FakeResp()

        monkeypatch.setattr(ask_brain.urllib.request, "urlopen", mock_urlopen)

        answer = ask_brain.generate_answer(
            "What is it?",
            context_chunks,
            lm_studio_url="http://localhost:1234/v1/chat/completions",
        )
        assert "answer" in answer.lower() or "42" in answer

    def test_handles_lm_studio_error(self, monkeypatch):
        """Should return an error message when LM Studio is unreachable."""
        def raise_urlerror(*args, **kwargs):
            raise ask_brain.urllib.error.URLError("Connection refused")

        monkeypatch.setattr(ask_brain.urllib.request, "urlopen", raise_urlerror)

        answer = ask_brain.generate_answer(
            "What?",
            [{"text": "context"}],
            lm_studio_url="http://localhost:1234/v1/chat/completions",
        )
        assert "Could not reach LM Studio" in answer

    def test_handles_empty_response(self, monkeypatch):
        """Should handle empty model response."""
        mock_response = {"choices": [{"message": {"content": ""}}]}

        def mock_urlopen(req, timeout=None):
            class FakeResp:
                status = 200
                def read(self):
                    return json.dumps(mock_response).encode("utf-8")
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    pass
            return FakeResp()

        monkeypatch.setattr(ask_brain.urllib.request, "urlopen", mock_urlopen)
        answer = ask_brain.generate_answer(
            "What?",
            [{"text": "context"}],
            lm_studio_url="http://localhost:1234/v1/chat/completions",
        )
        assert "empty response" in answer.lower()


# ---------------------------------------------------------------------------
# ask (main entry point)
# ---------------------------------------------------------------------------

class TestAsk:
    def test_ask_with_empty_index(self, tmp_path):
        """Should return a message when the index is empty."""
        empty_path = os.path.join(str(tmp_path), "empty.json")
        with open(empty_path, "w") as f:
            json.dump({}, f)
        # load_index calls sys.exit(1) on missing file, but empty dict is valid
        # So we need a file that loads but returns empty
        result = ask_brain.ask("test", index_path=empty_path)
        assert "No index available" in result or "empty" in result.lower()

    def test_ask_no_results(self, monkeypatch, tmp_path):
        """Should handle no search results gracefully."""
        index = {"doc.txt": {"chunks": []}}
        index_path = _write_temp_index(index, tmp_path)

        def mock_load(path):
            return index
        monkeypatch.setattr(ask_brain, "load_index", mock_load)

        result = ask_brain.ask("test", index_path=index_path)
        assert "No relevant context" in result

    def test_ask_falls_back_to_keyword_when_semantic_fails(self, monkeypatch, tmp_path):
        """Should fall back to keyword search if semantic search fails."""
        index = _make_index()
        index_path = _write_temp_index(index, tmp_path)

        def mock_load(path):
            return index
        monkeypatch.setattr(ask_brain, "load_index", mock_load)

        # Make semantic_search fail (LM Studio unreachable)
        def raise_urlerror(*args, **kwargs):
            raise ask_brain.urllib.error.URLError("No connection")

        monkeypatch.setattr(ask_brain.urllib.request, "urlopen", raise_urlerror)

        # Mock generate_answer to return a fixed answer
        monkeypatch.setattr(ask_brain, "generate_answer", lambda q, chunks, url: "Fallback answer")

        result = ask_brain.ask("document 0", index_path=index_path, use_semantic=True)
        assert "Fallback answer" in result
