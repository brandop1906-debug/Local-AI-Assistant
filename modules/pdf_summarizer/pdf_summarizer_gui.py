"""
pdf_summarizer_gui.py
=====================
A CustomTkinter GUI wrapper for pdf_summarizer.py.

Provides a modern interface to:
  - Select a PDF file
  - Configure summarization options
  - Summarize it using LM Studio
  - View, copy, and save the summary

Run with:
  python pdf_summarizer_gui.py
"""

import os
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog

# Add the script's directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import pdf_summarizer

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


class PDFSummarizerGUI:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("PDF Summarizer")
        self.root.geometry("800x750")
        self.root.minsize(550, 500)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.pdf_path = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Ready")
        self.is_running = False

        # Options
        self.summary_length = ctk.StringVar(value="medium")
        self.plain_english = ctk.BooleanVar(value=False)
        self.custom_save_path = ctk.StringVar(value="")

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.configure(fg_color=DARK_BG)

        # ---- Top accent bar ----
        accent_bar = ctk.CTkFrame(self.root, fg_color=ACCENT, height=3)
        accent_bar.pack(fill="x", side="top")
        accent_bar.pack_propagate(False)

        # ---- Scrollable content ----
        scroll = ctk.CTkScrollableFrame(
            self.root,
            fg_color=DARK_BG,
            border_color=DARK_BG,
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # --- Title ---
        title = ctk.CTkLabel(
            scroll,
            text="PDF Summarizer",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=WHITE,
        )
        title.pack(pady=(16, 4), anchor="w", padx=16)

        subtitle = ctk.CTkLabel(
            scroll,
            text="Upload a PDF and get an AI-powered summary",
            font=(FONT_FAMILY, 11),
            text_color=GRAY,
        )
        subtitle.pack(pady=(0, 12), anchor="w", padx=16)

        # --- File selection card ---
        self._build_file_card(scroll)

        # --- Options card ---
        self._build_options_card(scroll)

        # --- Action card ---
        self._build_action_card(scroll)

        # --- Status card ---
        self._build_status_card(scroll)

        # --- Preview card ---
        self._build_preview_card(scroll)

        # --- Result actions card ---
        self._build_result_actions_card(scroll)

    def _build_file_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(8, 8))

        label = ctk.CTkLabel(
            card,
            text="PDF File:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=GRAY,
            anchor="w",
        )
        label.pack(fill="x", padx=14, pady=(10, 4))

        path_frame = ctk.CTkFrame(card, fg_color=DARK_BG)
        path_frame.pack(fill="x", padx=14, pady=(0, 10))

        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.pdf_path,
            state="readonly",
            font=(FONT_FAMILY, 12),
            text_color=WHITE,
            placeholder_text_color=GRAY,
            fg_color=DARK_INPUT,
            corner_radius=10,
            height=40,
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse...",
            font=(FONT_FAMILY, 11),
            fg_color=ACCENT,
            hover_color="#5ba0e9",
            text_color=WHITE,
            corner_radius=10,
            width=90,
            height=40,
            command=self._browse_pdf,
        )
        self.browse_btn.pack(side="right")

    def _build_options_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(0, 8))

        label = ctk.CTkLabel(
            card,
            text="Options:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=GRAY,
            anchor="w",
        )
        label.pack(fill="x", padx=14, pady=(10, 6))

        opts_frame = ctk.CTkFrame(card, fg_color=DARK_BG)
        opts_frame.pack(fill="x", padx=14, pady=(0, 10))

        # Length selector
        length_label = ctk.CTkLabel(
            opts_frame,
            text="Summary Length:",
            font=(FONT_FAMILY, 10),
            text_color=GRAY,
        )
        length_label.pack(side="left", padx=(0, 8))

        self.length_combo = ctk.CTkComboBox(
            opts_frame,
            values=["short", "medium", "detailed"],
            variable=self.summary_length,
            font=(FONT_FAMILY, 11),
            fg_color=DARK_INPUT,
            button_color=ACCENT,
            button_hover_color="#5ba0e9",
            dropdown_fg_color="#1a1d27",
            width=120,
        )
        self.length_combo.pack(side="left", padx=(0, 20))

        # Plain English toggle
        self.plain_toggle = ctk.CTkSwitch(
            opts_frame,
            variable=self.plain_english,
            text="Rewrite in plain English",
            font=(FONT_FAMILY, 10),
            text_color=GRAY,
            fg_color=DARK_INPUT,
            button_color=ACCENT,
            button_hover_color="#5ba0e9",
            onvalue=1,
            offvalue=0,
        )
        self.plain_toggle.pack(side="left")

    def _build_action_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(0, 8))

        self.summarize_btn = ctk.CTkButton(
            card,
            text="Summarize PDF",
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=ACCENT,
            hover_color="#5ba0e9",
            text_color=WHITE,
            corner_radius=10,
            height=44,
            command=self._start_summarize,
        )
        self.summarize_btn.pack(fill="x", padx=14, pady=(10, 10))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            card,
            fg_color=DARK_INPUT,
            progress_color=ACCENT,
            corner_radius=6,
            height=8,
        )
        self.progress.pack(fill="x", padx=14, pady=(0, 6))
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(
            card,
            text="",
            font=(FONT_FAMILY, 9),
            text_color=GRAY,
        )
        self.progress_label.pack(pady=(0, 10))

    def _build_status_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(0, 8))

        self.status_label = ctk.CTkLabel(
            card,
            textvariable=self.status_var,
            font=(FONT_FAMILY, 10),
            text_color=GRAY,
            anchor="w",
        )
        self.status_label.pack(fill="x", padx=14, pady=10)

    def _build_preview_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        label = ctk.CTkLabel(
            card,
            text="Summary Preview:",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=GRAY,
            anchor="w",
        )
        label.pack(fill="x", padx=14, pady=(10, 4))

        self.summary_text = ctk.CTkTextbox(
            card,
            font=(FONT_FAMILY, 12),
            text_color=WHITE,
            fg_color=DARK_INPUT,
            corner_radius=10,
            state="disabled",
        )
        self.summary_text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

    def _build_result_actions_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=DARK_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=DARK_BORDER,
        )
        card.pack(fill="x", padx=16, pady=(0, 16))

        btn_frame = ctk.CTkFrame(card, fg_color=DARK_BG)
        btn_frame.pack(fill="x", padx=14, pady=(10, 10))

        self.copy_btn = ctk.CTkButton(
            btn_frame,
            text="Copy to Clipboard",
            font=(FONT_FAMILY, 11),
            fg_color=DARK_SURFACE,
            hover_color=ACCENT_GLOW,
            border_width=1,
            border_color=DARK_BORDER,
            text_color=GRAY,
            corner_radius=10,
            height=36,
            command=self._copy_to_clipboard,
            state="disabled",
        )
        self.copy_btn.pack(side="left")

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="Save As...",
            font=(FONT_FAMILY, 11),
            fg_color=DARK_SURFACE,
            hover_color=ACCENT_GLOW,
            border_width=1,
            border_color=DARK_BORDER,
            text_color=GRAY,
            corner_radius=10,
            height=36,
            command=self._save_as,
            state="disabled",
        )
        self.save_btn.pack(side="left", padx=(8, 0))

        self.save_path_label = ctk.CTkLabel(
            card,
            text="No file saved yet",
            font=(FONT_FAMILY, 9),
            text_color=GRAY,
            anchor="e",
        )
        self.save_path_label.pack(fill="x", padx=14, pady=(0, 10))

    # ------------------------------------------------------------------ #
    # File / browse helpers
    # ------------------------------------------------------------------ #

    def _browse_pdf(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if filepath:
            self.pdf_path.set(filepath)
            self.status_var.set("File selected. Click 'Summarize PDF' to begin.")

    def _set_status(self, message: str):
        self.status_var.set(message)
        self.root.update_idletasks()

    # ------------------------------------------------------------------ #
    # Summarization (runs in background thread)
    # ------------------------------------------------------------------ #

    def _start_summarize(self) -> None:
        if self.is_running:
            return

        pdf_path = self.pdf_path.get().strip()
        if not pdf_path or not os.path.isfile(pdf_path):
            ctk.CTkMessageDialog(
                parent=self.root,
                title="Error",
                anchor="center",
            ).show("Please select a valid PDF file first.")
            return

        self.is_running = True
        self.summarize_btn.configure(state="disabled")
        self.copy_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", "[Starting summarization...]\n")
        self.summary_text.configure(state="disabled")
        self._set_status("Starting summarization...")
        self._reset_progress()

        thread = threading.Thread(target=self._run_summarize, args=(pdf_path,), daemon=True)
        thread.start()

    def _progress_callback(self, status: str, current: int, total: int) -> None:
        """Callback called from the background thread to update progress."""
        pct = int((current / total) * 100) if total else 0
        self.root.after(0, self._update_progress, status, current, total, pct)

    def _update_progress(self, status: str, current: int, total: int, pct: int):
        self.progress.set(pct / 100)
        self.progress_label.configure(text=f"{current}/{total}")
        self.status_var.set(f"{status} ({current}/{total})")
        self.root.update_idletasks()

    def _reset_progress(self):
        self.progress.set(0)
        self.progress_label.configure(text="")

    def _run_summarize(self, pdf_path: str):
        try:
            self._set_status("Extracting text from PDF...")
            self.root.after(0, self._insert_preview, "[Extracting text...]\n")

            self._set_status("Checking LM Studio connection...")
            self.root.after(0, self._insert_preview, "[Checking LM Studio...]\n")

            if not pdf_summarizer.check_lm_studio_running():
                self.root.after(0, self._show_error, "LM Studio is not running.\nPlease start it and try again.")
                self.is_running = False
                return

            self._set_status("Summarizing chunks...")
            self.root.after(0, self._insert_preview, "[Summarizing...]\n")

            length = self.summary_length.get()
            plain = self.plain_english.get()

            filepath = pdf_summarizer.summarize_pdf(
                pdf_path,
                progress_callback=self._progress_callback,
                summary_length=length,
                plain_english=plain,
            )

            with open(filepath, "r", encoding="utf-8") as f:
                summary = f.read()

            self.root.after(0, self._show_success, summary, filepath)

        except Exception as e:
            self.root.after(0, self._show_error, str(e))
        finally:
            self.root.after(0, self.summarize_btn.config, state="normal")
            self.is_running = False

    def _insert_preview(self, text: str):
        self.summary_text.configure(state="normal")
        self.summary_text.insert("end", text)
        self.summary_text.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Result display
    # ------------------------------------------------------------------ #

    def _show_success(self, summary: str, filepath: str):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", summary)
        self.summary_text.configure(state="disabled")
        self._set_status(f"Done! Saved to: {filepath}")
        self.progress.set(1)
        self.progress_label.configure(text="Done")
        self.copy_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.save_path_label.configure(text=f"Auto-saved to: {filepath}")

        ctk.CTkMessageDialog(
            parent=self.root,
            title="Summary Complete",
            anchor="center",
        ).show(f"PDF summary saved to:\n\n{filepath}\n\nView the full summary in the preview above.")

    def _show_error(self, message: str):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", f"[ERROR]\n{message}")
        self.summary_text.configure(state="disabled")
        self._set_status("Error occurred.")

        ctk.CTkMessageDialog(
            parent=self.root,
            title="Error",
            anchor="center",
        ).show(message)

    # ------------------------------------------------------------------ #
    # Copy / Save helpers
    # ------------------------------------------------------------------ #

    def _copy_to_clipboard(self) -> None:
        summary = self.summary_text.get("1.0", "end").strip()
        if not summary:
            ctk.CTkMessageDialog(
                parent=self.root,
                title="Nothing to copy",
                anchor="center",
            ).show("The summary preview is empty.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(summary)
        self.root.update()
        self.status_var.set("Copied to clipboard!")
        ctk.CTkMessageDialog(
            parent=self.root,
            title="Copied",
            anchor="center",
        ).show("Summary copied to clipboard.")

    def _save_as(self) -> None:
        summary = self.summary_text.get("1.0", "end").strip()
        if not summary:
            ctk.CTkMessageDialog(
                parent=self.root,
                title="Nothing to save",
                anchor="center",
            ).show("The summary preview is empty.")
            return

        default_name = "summary.txt"
        saved_text = self.save_path_label.cget("text")
        if saved_text.startswith("Auto-saved to: "):
            auto_path = saved_text[len("Auto-saved to: "):]
            default_name = os.path.basename(auto_path)

        filepath = filedialog.asksaveasfilename(
            title="Save Summary As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=default_name,
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(summary)
            self.save_path_label.configure(text=f"Saved to: {filepath}")
            self._set_status(f"Saved to: {filepath}")
            ctk.CTkMessageDialog(
                parent=self.root,
                title="Saved",
                anchor="center",
            ).show(f"Summary saved to:\n\n{filepath}")
        except OSError as e:
            ctk.CTkMessageDialog(
                parent=self.root,
                title="Save Error",
                anchor="center",
            ).show(str(e))


def main() -> None:
    root = ctk.CTk()
    PDFSummarizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
