"""
gui.py — CustomTkinter GUI for the Business Brain.

Provides a modern graphical interface to:
  - Ask questions against your indexed documents
  - Re-index documents when needed
"""

import os
import sys
import json
import threading
import customtkinter as ctk

# ---------------------------------------------------------------------------
# Resolve paths so imports work whether launched from this directory or not
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import ask_brain
import indexer

# Theme colors
DARK_BG = "#0f1117"
DARK_SURFACE = "#1a1d27"
DARK_INPUT = "#161922"
DARK_BORDER = "#2a2e3a"
ACCENT = "#4a90d9"
ACCENT_GLOW = "#4a90d930"
WHITE = "#e8eaed"
GRAY = "#8b8fa3"
GREEN = "#4caf50"
RED = "#e74c3c"
YELLOW = "#f0a500"
FONT_FAMILY = "Segoe UI"


# ---------------------------------------------------------------------------
# Config helpers
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
    """Modern CustomTkinter application for the Business Brain."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Business Brain")
        self.root.geometry("800x700")
        self.root.minsize(500, 450)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        config = load_config()
        self.documents_dir = get_documents_dir(config)

        self._build_ui()

    def _build_ui(self):
        self.root.configure(fg_color=DARK_BG)

        # ---- Top accent bar ----
        accent_bar = ctk.CTkFrame(self.root, fg_color=ACCENT, height=3)
        accent_bar.pack(fill="x", side="top")
        accent_bar.pack_propagate(False)

        # ---- Header ----
        header = ctk.CTkFrame(self.root, fg_color=DARK_BG)
        header.pack(fill="x", padx=16, pady=(16, 4))

        title = ctk.CTkLabel(
            header,
            text="Business Brain",
            font=(FONT_FAMILY, 22, "bold"),
            text_color=WHITE,
        )
        title.pack(side="left")

        subtitle = ctk.CTkLabel(
            header,
            text="Ask questions about your documents",
            font=(FONT_FAMILY, 11),
            text_color=GRAY,
        )
        subtitle.pack(side="left", padx=(12, 0))

        # ---- Question input area ----
        input_card = ctk.CTkFrame(
            self.root,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        input_card.pack(fill="x", padx=16, pady=(8, 12))

        q_label = ctk.CTkLabel(
            input_card,
            text="Ask the Business Brain:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=GRAY,
            anchor="w",
        )
        q_label.pack(fill="x", padx=14, pady=(10, 4))

        self.question_var = ctk.StringVar(value="")
        self.question_entry = ctk.CTkEntry(
            input_card,
            textvariable=self.question_var,
            placeholder_text="e.g., What are the key points from the Q3 report?",
            font=(FONT_FAMILY, 13),
            text_color=WHITE,
            placeholder_text_color=GRAY,
            fg_color=DARK_INPUT,
            corner_radius=10,
            height=44,
        )
        self.question_entry.pack(fill="x", padx=14, pady=(0, 10))
        self.question_entry.bind("<Return>", lambda e: self._on_ask())

        btn_frame = ctk.CTkFrame(input_card, fg_color=DARK_BG)
        btn_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.ask_btn = ctk.CTkButton(
            btn_frame,
            text="Ask the Business Brain",
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=ACCENT,
            hover_color="#5ba0e9",
            text_color=WHITE,
            corner_radius=10,
            height=36,
            command=self._on_ask,
        )
        self.ask_btn.pack(side="left")

        self.reindex_btn = ctk.CTkButton(
            btn_frame,
            text="Re-index Documents",
            font=(FONT_FAMILY, 11),
            fg_color=DARK_SURFACE,
            hover_color=ACCENT_GLOW,
            border_width=1,
            border_color=DARK_BORDER,
            text_color=GRAY,
            corner_radius=10,
            height=36,
            command=self._on_reindex,
        )
        self.reindex_btn.pack(side="left", padx=(8, 0))

        # ---- Status label ----
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            self.root,
            textvariable=self.status_var,
            font=(FONT_FAMILY, 10),
            text_color=GRAY,
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=16, pady=(4, 8))

        # ---- Answer area ----
        answer_header = ctk.CTkFrame(self.root, fg_color=DARK_BG)
        answer_header.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            answer_header,
            text="Answer:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=GRAY,
            anchor="w",
        ).pack(anchor="w")

        self.answer_text = ctk.CTkTextbox(
            self.root,
            font=(FONT_FAMILY, 12),
            text_color=WHITE,
            fg_color=DARK_INPUT,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
            state="disabled",
        )
        self.answer_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _set_status(self, message: str):
        """Update the status label."""
        self.status_var.set(message)
        self.root.update_idletasks()

    def _append_answer(self, text: str):
        """Set text in the answer display area."""
        self.answer_text.configure(state="normal")
        self.answer_text.delete("1.0", "end")
        self.answer_text.insert("1.0", text)
        self.answer_text.configure(state="disabled")

    def _on_ask(self):
        """Handle the Ask button click."""
        question = self.question_var.get().strip()
        if not question:
            self._set_status("⚠ Please enter a question.")
            return

        self._set_status("Searching and generating answer…")
        self._append_answer("Loading…")

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
        self._set_status("Indexing documents… This may take a moment.")

        thread = threading.Thread(target=self._reindex_worker, daemon=True)
        thread.start()

    def _reindex_worker(self):
        """Worker thread that runs the indexer and shows a popup on completion."""
        try:
            config = load_config()
            indexer.index_documents(config, force_reindex=True)
            self.root.after(0, self._set_status, "Ready")
            self.root.after(0, self._show_info, "Indexing Complete",
                          "Documents have been re-indexed successfully!")
        except Exception as exc:
            self.root.after(0, self._set_status, f"Indexing failed: {exc}")
            self.root.after(0, self._show_error, "Indexing Failed",
                          f"An error occurred during indexing:\n{exc}")

    def _show_info(self, title: str, message: str):
        ctk.CTkMessageDialog(
            parent=self.root,
            title=title,
            anchor="center",
        ).show(message)

    def _show_error(self, title: str, message: str):
        ctk.CTkMessageDialog(
            parent=self.root,
            title=title,
            anchor="center",
        ).show(message)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    root = ctk.CTk()
    BusinessBrainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
