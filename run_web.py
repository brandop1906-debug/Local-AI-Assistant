"""
run_web.py
==========
Launcher for the pywebview-based Local AI Assistant.

Starts a local FastAPI server and opens it in a system webview window.
100% offline — no cloud dependencies.

Usage:
    python run_web.py
"""

import os
import sys

# Ensure project root is on sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

if __name__ == "__main__":
    from utils.logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger("launcher")

    logger.info("Starting Local AI Assistant...")
    logger.info("  Local server: http://127.0.0.1:18765/")
    logger.info("  LM Studio must be running for AI features")

    try:
        from app.main import main
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted. Shutting down.")
        sys.exit(0)
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        logger.error("Install web dependencies: pip install pywebview fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unhandled error during startup")
        sys.exit(1)
