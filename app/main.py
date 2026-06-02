"""
app/main.py
===========
pywebview + FastAPI launcher for the Local AI Assistant.

Runs a local FastAPI server and opens it in a pywebview window.
100% offline — no cloud dependencies.

Usage:
    python run_web.py
"""

import json
import os
import sys
import threading
import webview

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

from utils.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger("app.main")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.dirname(SCRIPT_DIR))  # Local AI Assistant (project root)

# Package imports — no sys.path manipulation needed when installed via pip
from modules.chat_ai.chat import ask_ai
from modules.chat_history import (
    new_session,
    get_sessions,
    clear_all_sessions,
    load_session,
    save_message,
    rename_session,
    delete_session,
)
from modules import email_assistant
from modules import pdf_summarizer
from modules import quote_generator
from business_brain import ask_brain
from business_brain.indexer import index_documents

logger.debug("PROJECT_DIR=%s", PROJECT_DIR)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Local AI Assistant")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=os.path.join(SCRIPT_DIR, "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the main HTML page."""
    with open(os.path.join(SCRIPT_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# ---------------------------------------------------------------------------
# API routes — proxy to existing Python modules
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def api_chat(data: dict):
    """Chat with the local LLM."""
    text = data.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    try:
        response = ask_ai(text)
        return {"response": response}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/email")
def api_email(data: dict):
    """Generate an email draft."""
    topic = data.get("topic", "").strip()
    tone = data.get("tone", "professional")

    if not topic:
        return JSONResponse({"error": "Please describe the email you want to write."}, status_code=400)

    try:
        template_text = email_assistant.load_template(tone)
        full_prompt = (
            f"{template_text}\n\n"
            f"Email topic / summary:\n{topic}\n\n"
            f"Please write the complete email based on the topic above.\n"
            f"Include a subject line and the email body."
        )
        email_content = email_assistant.call_lm_studio(full_prompt)

        # Save to output folder
        email_assistant.ensure_dir(email_assistant.OUTPUT_DIR)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(email_assistant.OUTPUT_DIR, f"email_{ts}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(email_content)

        return {"response": email_content, "filepath": filepath}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/pdf/summarize")
def api_pdf_summarize(data: dict):
    """Summarize a PDF file (sent as base64)."""
    file_data = data.get("file_data", "")
    filename = data.get("filename", "document.pdf")

    if not file_data:
        return JSONResponse({"error": "Please select a PDF file."}, status_code=400)

    # Write the base64 file to a temp location
    import base64, tempfile
    tmp_dir = tempfile.mkdtemp(prefix="localai_pdf_")
    tmp_path = os.path.join(tmp_dir, filename)

    try:
        with open(tmp_path, "wb") as f:
            f.write(base64.b64decode(file_data))

        def progress_cb(status, current, total):
            pass

        length = data.get("summary_length", "medium")
        plain = data.get("plain_english", False)

        result_path = pdf_summarizer.summarize_pdf(
            tmp_path,
            progress_callback=progress_cb,
            summary_length=length,
            plain_english=plain,
        )

        with open(result_path, "r", encoding="utf-8") as f:
            summary = f.read()

        # Use json.dumps with ensure_ascii=True to avoid Windows charmap issues
        # when the LLM output contains emoji or other non-ASCII characters
        import json as _json
        return JSONResponse(
            content=_json.loads(_json.dumps({"response": summary, "filepath": result_path}, ensure_ascii=True))
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Clean up temp file
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@app.post("/api/quote")
def api_quote(data: dict):
    """Generate a service quote."""
    try:
        category = data.get("category", "General Handyman")
        customer_name = data.get("customer_name", "")
        customer_phone = data.get("customer_phone", "")
        customer_address = data.get("customer_address", "")
        services_desc = data.get("services_desc", "")
        pricing_items = data.get("pricing_items", [])

        # Build customer info
        customer_lines = []
        if customer_name:
            customer_lines.append(f"Customer Name: {customer_name}")
        if customer_phone:
            customer_lines.append(f"Phone: {customer_phone}")
        if customer_address:
            customer_lines.append(f"Address: {customer_address}")
        customer_block = "\n".join(customer_lines) if customer_lines else "Customer information will be filled in upon acceptance."

        # Build pricing section
        pricing_block = ""
        if pricing_items:
            pricing_lines = ["Pricing Breakdown:"]
            for i, item in enumerate(pricing_items, 1):
                pricing_lines.append(
                    f"  {i}. {item['description']}  |  Qty: {item['qty']}  |  Unit: ${item['price']:,.2f}  |  Total: ${item['total']:,.2f}"
                )
            subtotal = sum(item["total"] for item in pricing_items)
            tax = subtotal * 0.10
            grand = subtotal + tax
            pricing_lines.append(f"\n  Subtotal: ${subtotal:,.2f}")
            pricing_lines.append(f"  Tax (10%):  ${tax:,.2f}")
            pricing_lines.append(f"  **Total: ${grand:,.2f}**")
            pricing_block = "\n".join(pricing_lines)

        # Load template
        template_text = quote_generator.load_template("quote_base")

        full_prompt = f"""{template_text}

=== INPUT DATA ===

Service Category: {category}

{customer_block}

Services / Project Description:
{services_desc}

{pricing_block}

==================

Please generate a complete, professional service quote based on the data above.
Include all standard sections: Header, Client Info, Scope of Work, Pricing, Terms, Contact.
Use the provided pricing data exactly as given. If the pricing section is empty, generate reasonable estimates.
Format the quote as a clean, ready-to-use document.
"""

        quote_content = quote_generator.call_lm_studio(full_prompt)

        # Save
        quote_generator.ensure_dir(quote_generator.OUTPUT_DIR)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(quote_generator.OUTPUT_DIR, f"quote_{ts}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(quote_content)

        return {"response": quote_content, "filepath": filepath}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/brain/ask")
def api_brain_ask(data: dict):
    """Ask a question against the Business Brain documents."""
    question = data.get("question", "").strip()

    if not question:
        return JSONResponse({"error": "Please enter a question."}, status_code=400)

    try:
        answer = ask_brain.ask(question, use_semantic=True)
        return {"response": answer}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/brain/reindex")
def api_brain_reindex():
    """Re-index the Business Brain documents."""
    try:
        index_documents(force_reindex=True)
        return {"status": "ok", "message": "Documents re-indexed successfully."}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat/history")
async def api_new_session(request: Request):
    """Create a new chat session."""
    try:
        body = json.loads(await request.body())
        name = body.get('name', 'Untitled')
        session = new_session(name=name)
        return {"session": session}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/chat/history")
def api_list_sessions():
    """List all chat sessions."""
    try:
        sessions = get_sessions()
        return {"sessions": sessions}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat/history/clear")
def api_clear_sessions():
    """Clear all chat sessions."""
    try:
        count = clear_all_sessions()
        return {"status": "cleared", "deleted": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/chat/history/{session_id}")
def api_load_session(session_id: str):
    """Load a specific session."""
    try:
        session = load_session(session_id)
        if session is None:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        return {"session": session}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/chat/history/{session_id}")
async def api_rename_session(session_id: str, request: Request):
    """Rename a session."""
    try:
        body = json.loads(await request.body())
        name = body.get('name', '').strip()
        if not name:
            return JSONResponse({"error": "Name cannot be empty"}, status_code=400)
        session = rename_session(session_id, name)
        if session is None:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        return {"session": session}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/chat/history/{session_id}")
def api_delete_session(session_id: str):
    """Delete a session."""
    try:
        deleted = delete_session(session_id)
        if not deleted:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        return {"status": "deleted"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/chat/{session_id}")
def api_chat_with_session(session_id: str, data: dict):
    """Chat with the local LLM and save to a session."""
    text = data.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    try:
        save_message(session_id, "user", text)
        response = ask_ai(text)
        save_message(session_id, "ai", response)

        return {"response": response, "session_id": session_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/health")
def api_health():
    """Health check — verifies LM Studio is reachable."""
    try:
        import urllib.request
        endpoints = [
            "http://127.0.0.1:1234/v1/models",
            "http://127.0.0.1:1234/health",
        ]
        for url in endpoints:
            try:
                resp = urllib.request.urlopen(url, timeout=5)
                if resp.status == 200:
                    return {"lm_studio": "ok"}
            except Exception:
                continue
        return {"lm_studio": "unreachable", "message": "LM Studio not detected. Start it and try again."}
    except Exception as e:
        return {"lm_studio": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_fastapi():
    """Run FastAPI in a background thread."""
    import uvicorn

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=18765,
        log_level="error",  # quiet — no console spam
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    """Start the FastAPI server and open the pywebview window."""
    # Start FastAPI in background thread
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()

    # Give the server a moment to start
    import time
    time.sleep(0.5)

    # Open the window
    window = webview.create_window(
        title="Local AI Assistant",
        url="http://127.0.0.1:18765/",
        width=1100,
        height=750,
        min_size=(600, 500),
        resizable=True,
        background_color="#0d1117",
        text_select=True,
        js_api=None,  # We communicate via HTTP, not js_api
    )

    try:
        webview.start()
    except KeyboardInterrupt:
        logger.info("Interrupted. Shutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
