# Local AI Assistant

A 100% offline, desktop AI assistant built with Python, FastAPI, and pywebview. Runs locally — no cloud APIs, no internet required.

## Features

- **AI Chat** — Chat with a local LLM (via LM Studio) with RAG over your project documents
- **Business Brain** — Ask questions against indexed documents (FAQs, policies, pricing, procedures, templates)
- **Email Drafting** — Generate professional email drafts using your templates
- **PDF Summarization** — Upload and summarize PDF documents
- **Service Quotes** — Generate professional service quotes with pricing breakdowns
- **Chat History** — Persistent sessions stored locally as JSON files

## Prerequisites

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) running with a model loaded (default: `localhost:1234`)

## Installation

```bash
# Install the package in editable mode (recommended)
pip install -e .

# Or install optional extras:
pip install -e ".[pdf,docx,indexer]"   # PDF/DOCX support + document indexer
pip install -e ".[dev]"                  # dev dependencies (pytest, httpx)
```

## Running

```bash
python run_web.py
```

This starts a local FastAPI server and opens the app in a system webview window.

- Local server: `http://127.0.0.1:18765/`
- Check LM Studio connectivity: `GET /api/health`

## Architecture

```
run_web.py          → Launcher (entry point)
app/main.py         → FastAPI server + pywebview window
app/                → Frontend (HTML/CSS/JS)
modules/            → Feature modules
  chat_ai/          → Local LLM chat with RAG
  email_assistant/  → Email template generation
  pdf_summarizer/   → PDF upload & summarization
  quote_generator/  → Service quote generation
  chat_history.py   → Session storage (JSON files)
business_brain/     → Document indexing & semantic search
```

## Configuration

Each module has its own `config.json`. The root `config.json` controls:

- **App name** (`app_name`)
- **Default model** (`model`)
- **Active modules** (which modules are registered in the launcher)

Each module's `config.json` holds its own LM Studio URL, model, temperature, and max token settings.

### Config files

| File | Purpose |
|---|---|
| `config.json` | Root config (LM Studio URL, API keys) |
| `modules/chat_ai/config.json` | Model, temperature, max tokens, system prompt |
| `modules/email_assistant/config.json` | Email templates & settings |
| `modules/pdf_summarizer/config.json` | Summary length, plain English toggle |
| `modules/quote_generator/config.json` | Quote templates & pricing defaults |
| `business_brain/config.json` | Embedding model, LM Studio URL for indexing |

## Chat History

Sessions are stored in `.local/chat_history/` as individual JSON files. Limits are enforced automatically:

- Max **100 sessions** — oldest session deleted when exceeded
- Max **200 messages per session** — oldest messages trimmed on append

Both limits are configurable via `MAX_SESSIONS` and `MAX_MESSAGES_PER_SESSION` in `modules/chat_history.py`.

## Logs

Application logs are written to `.local/logs/app.log` (rotating, 5 MB max, 5 backups).
Useful for debugging issues that don't surface in the app UI.

## Troubleshooting

- **"LM Studio not detected"** — Ensure LM Studio is running and a model is loaded
- **Empty responses** — Check that the correct model is loaded in LM Studio
- **Import errors** — Reinstall the package: `pip install -e .`
