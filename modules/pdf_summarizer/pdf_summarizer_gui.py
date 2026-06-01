"""
pdf_summarizer_gui.py
=====================
A Tkinter GUI wrapper for pdf_summarizer.py.

Provides a simple interface to:
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
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Add the script's directory to sys.path so we can import pdf_summarizer
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import pdf_summarizer


class PDFSummarizerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Summarizer")
        self.root.geometry("750x700")
        self.root.resizable(True, True)
        self.root.minsize(550, 500)
        self.pdf_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.is_running = False

        # Summarization options
        self.summary_length = tk.StringVar(value="medium")
        self.plain_english = tk.BooleanVar(value=False)
        # Custom save path (None = auto-generate filename in output folder)
        self.custom_save_path = tk.StringVar(value="")

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI layout
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        # ---- Top frame: file selection + options ----
        top_frame = tk.Frame(self.root, padx=10, pady=8)
        top_frame.pack(fill=tk.X)

        # --- File selection row ---
        tk.Label(top_frame, text="PDF File:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        path_frame = tk.Frame(top_frame)
        path_frame.grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=(0, 5))
        path_frame.columnconfigure(0, weight=1)

        tk.Entry(
            path_frame,
            textvariable=self.pdf_path,
            state="readonly",
            bg="#f0f0f0",
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        tk.Button(
            path_frame,
            text="Browse...",
            command=self._browse_pdf,
            width=10,
        ).pack(side=tk.RIGHT)

        # --- Options row: summary length + plain English ---
        tk.Label(top_frame, text="Summary Length:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(4, 0))

        length_frame = tk.Frame(top_frame)
        length_frame.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(4, 0))

        ttk.Combobox(
            length_frame,
            textvariable=self.summary_length,
            values=["short", "medium", "detailed"],
            state="readonly",
            width=14,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT)

        tk.Label(top_frame, text="Plain English:", font=("Segoe UI", 9, "bold")).grid(row=1, column=2, sticky=tk.W, padx=(10, 5), pady=(4, 0))

        ttk.Checkbutton(
            top_frame,
            variable=self.plain_english,
            text="Rewrite in plain English",
        ).grid(row=1, column=3, sticky=tk.W, pady=(4, 0))

        # Make column 1 expand to fill space
        top_frame.columnconfigure(1, weight=1)

        # --- Frame: action buttons ---
        btn_frame = tk.Frame(self.root, padx=10, pady=6)
        btn_frame.pack(fill=tk.X)

        self.summarize_btn = tk.Button(
            btn_frame,
            text="Summarize PDF",
            command=self._start_summarize,
            width=20,
            font=("Segoe UI", 11, "bold"),
        )
        self.summarize_btn.pack(side=tk.LEFT)

        # Progress bar
        self.progress = ttk.Progressbar(btn_frame, mode="determinate", length=200)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        self.progress_label = tk.Label(btn_frame, text="", font=("Segoe UI", 8), fg="#555")
        self.progress_label.pack(side=tk.LEFT, padx=(6, 0))

        # --- Frame: status ---
        status_frame = tk.Frame(self.root, padx=10, pady=2)
        status_frame.pack(fill=tk.X)

        tk.Label(
            status_frame,
            textvariable=self.status_var,
            anchor=tk.W,
            font=("Segoe UI", 9),
            fg="#555",
        ).pack(fill=tk.X)

        # --- Frame: summary preview ---
        preview_frame = tk.Frame(self.root, padx=10, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(preview_frame, text="Summary Preview:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        # Text + scrollbar
        text_scroll = tk.Frame(preview_frame)
        text_scroll.pack(fill=tk.BOTH, expand=True)

        self.summary_text = tk.Text(
            text_scroll,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#fafafa",
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_scroll, command=self.summary_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.config(yscrollcommand=scrollbar.set)

        # --- Frame: summary action buttons ---
        action_frame = tk.Frame(self.root, padx=10, pady=10)
        action_frame.pack(fill=tk.X)

        # Left side: action buttons
        btn_row = tk.Frame(action_frame)
        btn_row.pack(side=tk.LEFT)

        self.copy_btn = tk.Button(
            btn_row,
            text="Copy to Clipboard",
            command=self._copy_to_clipboard,
            width=20,
            font=("Segoe UI", 10),
            state=tk.DISABLED,
            bg="#e8f4e8",
            activebackground="#c8e4c8",
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.save_btn = tk.Button(
            btn_row,
            text="Save As...",
            command=self._save_as,
            width=14,
            font=("Segoe UI", 10),
            state=tk.DISABLED,
            bg="#e8f0f8",
            activebackground="#c8dce8",
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 6))

        # Right side: save path info
        self.save_path_label = tk.Label(
            action_frame,
            text="No file saved yet",
            font=("Segoe UI", 9),
            fg="#aaa",
            anchor=tk.E,
        )
        self.save_path_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

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

    def _set_status(self, message: str) -> None:
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
            messagebox.showerror("Error", "Please select a valid PDF file first.")
            return

        self.is_running = True
        self.summarize_btn.config(state=tk.DISABLED)
        self.copy_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "[Starting summarization...]\n")
        self._set_status("Starting summarization...")
        self._reset_progress()

        # Run in a thread so the GUI stays responsive
        thread = threading.Thread(target=self._run_summarize, args=(pdf_path,), daemon=True)
        thread.start()

    def _progress_callback(self, status: str, current: int, total: int) -> None:
        """Callback called from the background thread to update progress."""
        pct = int((current / total) * 100) if total else 0
        self.root.after(0, self._update_progress, status, current, total, pct)

    def _update_progress(self, status: str, current: int, total: int, pct: int) -> None:
        self.progress["value"] = pct
        self.progress_label.config(text=f"{current}/{total}")
        self.status_var.set(f"{status} ({current}/{total})")
        self.root.update_idletasks()

    def _reset_progress(self) -> None:
        self.progress["value"] = 0
        self.progress_label.config(text="")

    def _run_summarize(self, pdf_path: str) -> None:
        try:
            self._set_status("Extracting text from PDF...")
            self.root.after(0, self.summary_text.insert, tk.END, "[Extracting text...]\n")

            self._set_status("Checking LM Studio connection...")
            self.root.after(0, self.summary_text.insert, tk.END, "[Checking LM Studio...]\n")

            if not pdf_summarizer.check_lm_studio_running():
                self.root.after(0, self._show_error, "LM Studio is not running.\nPlease start it and try again.")
                self.is_running = False
                return

            self._set_status("Summarizing chunks...")
            self.root.after(0, self.summary_text.insert, tk.END, "[Summarizing...]\n")

            # Gather options from GUI
            length = self.summary_length.get()
            plain = self.plain_english.get()

            # Run the summarization pipeline
            filepath = pdf_summarizer.summarize_pdf(
                pdf_path,
                progress_callback=self._progress_callback,
                summary_length=length,
                plain_english=plain,
            )

            # Read the saved summary
            with open(filepath, "r", encoding="utf-8") as f:
                summary = f.read()

            # Show in GUI
            self.root.after(0, self._show_success, summary, filepath)

        except Exception as e:
            self.root.after(0, self._show_error, str(e))
        finally:
            self.root.after(0, self.summarize_btn.config, tk.NORMAL)
            self.is_running = False

    # ------------------------------------------------------------------ #
    # Result display
    # ------------------------------------------------------------------ #

    def _show_success(self, summary: str, filepath: str) -> None:
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary)
        self._set_status(f"Done! Saved to: {filepath}")
        self.progress["value"] = 100
        self.progress_label.config(text="Done")
        self.copy_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.save_path_label.config(text=f"Auto-saved to: {filepath}")
        messagebox.showinfo(
            "Summary Complete",
            f"PDF summary saved to:\n\n{filepath}\n\nView the full summary in the preview above.",
        )

    def _show_error(self, message: str) -> None:
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, f"[ERROR]\n{message}")
        self._set_status("Error occurred.")
        messagebox.showerror("Error", message)

    # ------------------------------------------------------------------ #
    # Copy / Save helpers
    # ------------------------------------------------------------------ #

    def _copy_to_clipboard(self) -> None:
        summary = self.summary_text.get("1.0", tk.END).strip()
        if not summary:
            messagebox.showwarning("Nothing to copy", "The summary preview is empty.")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(summary)
            self.root.update()  # needed to keep the clipboard alive
            self.status_var.set("Copied to clipboard!")
            messagebox.showinfo("Copied", "Summary copied to clipboard.")
        except tk.TclError as e:
            messagebox.showerror("Clipboard Error", str(e))

    def _save_as(self) -> None:
        summary = self.summary_text.get("1.0", tk.END).strip()
        if not summary:
            messagebox.showwarning("Nothing to save", "The summary preview is empty.")
            return

        # Determine default filename from the auto-saved path
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
            return  # user cancelled

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(summary)
            self.save_path_label.config(text=f"Saved to: {filepath}")
            self._set_status(f"Saved to: {filepath}")
            messagebox.showinfo("Saved", f"Summary saved to:\n\n{filepath}")
        except OSError as e:
            messagebox.showerror("Save Error", str(e))


def main() -> None:
    root = tk.Tk()
    PDFSummarizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
