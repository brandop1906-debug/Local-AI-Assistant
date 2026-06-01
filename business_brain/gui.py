"""
gui.py — Tkinter GUI for the Business Brain.

Provides a simple graphical interface to:
  - Ask questions against your indexed documents
  - Re-index documents when needed
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ---------------------------------------------------------------------------
# Resolve paths so imports work whether launched from this directory or not
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import ask_brain
import indexer


# ---------------------------------------------------------------------------
# Config helpers (mirrors config.json schema)
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load config.json from the same directory as this script."""
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_documents_dir(config: dict) -> str:
    """Return the absolute path to the documents directory."""
    base = os.path.dirname(os.path.abspath(__file__))
    rel = config.get("documents_dir", "documents")
    return os.path.join(base, rel)


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class BusinessBrainGUI:
    """Main Tkinter application for the Business Brain."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Business Brain")
        self.root.geometry("750x650")
        self.root.minsize(500, 400)

        config = load_config()
        self.documents_dir = get_documents_dir(config)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Construct the entire GUI layout."""

        # --- Top frame: question input + ask button ---
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Ask the Business Brain:").pack(anchor=tk.W)

        self.question_var = tk.StringVar()
        question_entry = ttk.Entry(
            top_frame, textvariable=self.question_var, width=70
        )
        question_entry.pack(fill=tk.X, pady=(5, 5))
        question_entry.bind("<Return>", lambda e: self._on_ask())

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(
            btn_frame, text="Ask the Business Brain", command=self._on_ask
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame, text="Re-index Documents", command=self._on_reindex
        ).pack(side=tk.LEFT)

        # --- Status label ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            self.root, textvariable=self.status_var, foreground="#555555"
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        # --- Answer display area ---
        ttk.Label(self.root, text="Answer:").pack(anchor=tk.W, padx=10)
        self.answer_text = scrolledtext.ScrolledText(
            self.root, width=90, height=20, wrap=tk.WORD, state=tk.DISABLED
        )
        self.answer_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _set_status(self, message: str):
        """Update the status label."""
        self.status_var.set(message)
        self.root.update_idletasks()

    def _append_answer(self, text: str):
        """Append text to the answer display area."""
        self.answer_text.config(state=tk.NORMAL)
        self.answer_text.delete("1.0", tk.END)
        self.answer_text.insert(tk.END, text)
        self.answer_text.config(state=tk.DISABLED)

    def _on_ask(self):
        """Handle the Ask button click."""
        question = self.question_var.get().strip()
        if not question:
            self._set_status("⚠ Please enter a question.")
            return

        self._set_status("Searching and generating answer…")
        self._append_answer("Loading…")

        # Run in a background thread to keep the GUI responsive
        thread = threading.Thread(target=self._ask_worker, args=(question,), daemon=True)
        thread.start()

    def _ask_worker(self, question: str):
        """Worker thread that calls ask_brain and updates the GUI."""
        try:
            answer = ask_brain.ask(question, use_semantic=True)
            self.root.after(0, self._append_answer, answer)
            self.root.after(0, self._set_status, "Done")
        except Exception as exc:
            self.root.after(0, self._append_answer, f"Error: {exc}")
            self.root.after(0, self._set_status, "Error")

    def _on_reindex(self):
        """Handle the Re-index button click."""
        # Disable button during indexing
        self._set_status("Indexing documents… This may take a moment.")

        # Run indexing in a background thread
        thread = threading.Thread(target=self._reindex_worker, daemon=True)
        thread.start()

    def _reindex_worker(self):
        """Worker thread that runs the indexer and shows a popup on completion."""
        try:
            config = load_config()
            indexer.index_documents(config, force_reindex=True)
            self.root.after(
                0,
                messagebox.showinfo,
                "Indexing Complete",
                "Documents have been re-indexed successfully!",
            )
            self.root.after(0, self._set_status, "Ready")
        except Exception as exc:
            self.root.after(0, self._set_status, f"Indexing failed: {exc}")
            self.root.after(
                0,
                messagebox.showerror,
                "Indexing Failed",
                f"An error occurred during indexing:\n{exc}",
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    BusinessBrainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
