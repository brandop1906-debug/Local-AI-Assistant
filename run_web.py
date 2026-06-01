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
    print("Starting Local AI Assistant...")
    print("  - Local server: http://127.0.0.1:18765/")
    print("  - LM Studio must be running for AI features")
    print()

    try:
        from app.main import main
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Closed.")
        sys.exit(0)
    except ImportError as e:
        print(f"\n[ERROR] Missing dependency: {e}")
        print("\nInstall web dependencies:")
        print("  pip install pywebview fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
