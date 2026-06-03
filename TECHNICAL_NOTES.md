# Technical Notes

A record of known technical debt and architectural decisions, with current status.

---

### 1. Tests ✅ DONE

A comprehensive test suite was added covering FastAPI routes, chat history CRUD, business brain search, chat module, and the document indexer. Tests use isolated fixtures and mock LM Studio responses.

---

### 2. subprocess + curl for HTTP calls ✅ DONE

`modules/chat_ai/chat.py` now uses `requests.post()` for all LM Studio calls. Error handling uses `requests.exceptions.Timeout` and `requests.exceptions.ConnectionError`. Tests updated to mock `requests.post` instead of `subprocess.run`.

---

### 3. sys.path manipulation ✅ DONE

Package structure was cleaned up — `__init__.py` files added to `modules/`, `business_brain/`, and `utils/`. The project can now be installed via `pip install -e .` which eliminates sys.path hacks.

---

### 4. Logging ✅ DONE

`utils/logging_config.py` added with a rotating file handler (5 MB, 5 backups). Adopted in `app/main.py`, `run_web.py`, and backend modules. Some route handlers still have sparse logging — worth filling in over time.

---

### 5. Chat history retention ✅ DONE

`chat_history.py` now enforces:
- Max 100 sessions (oldest auto-deleted when exceeded)
- Max 200 messages per session (oldest trimmed on append)

Constants `MAX_SESSIONS` and `MAX_MESSAGES_PER_SESSION` are defined at the top of the file.

---

### 6. README ✅ DONE

`README.md` added at project root with setup instructions, architecture overview, config reference, and troubleshooting guide.
