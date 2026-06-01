"""
chat_ai/gui.py
==============
Tkinter GUI for the Local AI Assistant chat module.

Displays a conversation log, accepts user input, and calls
chat.ask_ai() to get responses from the local LM Studio model.

Run with:
    python gui.py
"""

import tkinter as tk
from tkinter import scrolledtext, font as tkfont
import threading

# Import the chat module — assumes this file lives inside chat_ai/
from chat_ai.chat import ask_ai


class ChatGUI:
    """Simple Tkinter chat window backed by the local LM Studio model."""

    # ------------------------------------------------------------------
    # Colours & fonts
    # ------------------------------------------------------------------
    BG_COLOR = "#1e1e1e"
    FG_COLOR = "#d4d4d4"
    ENTRY_BG = "#2d2d2d"
    ENTRY_FG = "#ffffff"
    BUTTON_BG = "#0e639c"
    BUTTON_FG = "#ffffff"
    THINKING_FG = "#f0a500"

    FONT_FAMILY = "Consolas"
    FONT_SIZE = 12

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Local AI Assistant")
        self.root.geometry("700x500")
        self.root.configure(bg=self.BG_COLOR)

        # Flag to prevent double-submit while the model is responding
        self._is_responding = False

        self._build_ui()

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Create and pack every widget."""

        # -- Chat history (scrolling text area) --------------------------------
        self.chat_box = scrolledtext.ScrolledText(
            self.root,
            state="disabled",
            wrap="word",
            bg=self.BG_COLOR,
            fg=self.FG_COLOR,
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            insertbackground=self.FG_COLOR,
            relief="flat",
        )
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)

        # -- Status label (shows "Thinking..." while model responds) -----------
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            anchor="w",
            bg=self.BG_COLOR,
            fg=self.THINKING_FG,
            font=(self.FONT_FAMILY, 9),
        )
        self.status_label.pack(fill="x", padx=10, pady=(0, 2))

        # -- Bottom bar: entry + buttons --------------------------------------
        bottom_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        bottom_frame.pack(fill="x", padx=10, pady=(2, 10))

        self.entry = tk.Entry(
            bottom_frame,
            font=(self.FONT_FAMILY, self.FONT_SIZE),
            bg=self.ENTRY_BG,
            fg=self.ENTRY_FG,
            insertbackground=self.FG_COLOR,
            relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", self._on_send)

        # Send button
        send_btn = tk.Button(
            bottom_frame,
            text="Send",
            command=self._on_send,
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            activebackground="#1177bb",
            activeforeground=self.BUTTON_FG,
            font=(self.FONT_FAMILY, 10, "bold"),
            relief="flat",
            padx=18,
            pady=4,
        )
        send_btn.pack(side="left")

        # Clear button
        clear_btn = tk.Button(
            bottom_frame,
            text="Clear Chat",
            command=self._on_clear,
            bg="#555555",
            fg=self.BUTTON_FG,
            activebackground="#777777",
            activeforeground=self.BUTTON_FG,
            font=(self.FONT_FAMILY, 10),
            relief="flat",
            padx=18,
            pady=4,
        )
        clear_btn.pack(side="left", padx=(6, 0))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_send(self, _event=None):
        """Handle Send button click or Enter key press."""
        # Ignore if already processing
        if self._is_responding:
            return

        message = self.entry.get().strip()
        if not message:
            return

        # Clear the entry field
        self.entry.delete(0, tk.END)

        # Show the user's message in the chat
        self._append(f"[You]   {message}")

        # Lock the UI
        self._is_responding = True
        self._set_status("Thinking...", fg=self.THINKING_FG)
        self.entry.config(state="disabled")
        send_btn = self.root.winfo_children()[-1].winfo_children()[0]
        send_btn.config(state="disabled")

        # Run ask_ai in a background thread so the GUI stays responsive
        thread = threading.Thread(
            target=self._handle_response, args=(message,), daemon=True
        )
        thread.start()

    def _handle_response(self, user_message: str):
        """Background thread: call ask_ai() and update the GUI on return."""
        try:
            response = ask_ai(user_message)
        except Exception as exc:
            response = None
            error_msg = str(exc)

        # Schedule the update on the main (GUI) thread
        self.root.after(0, self._finalize_response, response, error_msg if 'error_msg' in dir() else None)

    def _finalize_response(self, response: str | None, error_msg: str | None):
        """Restore UI state and display the result."""
        self._is_responding = False
        self.entry.config(state="normal")
        self.entry.focus()

        # Re-reference the send button (it may have been recreated)
        bottom_frame = self.root.winfo_children()[-1]
        send_btn = bottom_frame.winfo_children()[0]
        send_btn.config(state="normal")

        if response is not None:
            self._append(f"[AI]    {response}")
            self._set_status("Ready", fg=self.FG_COLOR)
        else:
            self._append(f"[ERROR] {error_msg}")
            self._set_status("Error", fg="#e74c3c")

    def _on_clear(self):
        """Clear the conversation history."""
        self.chat_box.config(state="normal")
        self.chat_box.delete("1.0", tk.END)
        self.chat_box.config(state="disabled")
        self._set_status("Ready", fg=self.FG_COLOR)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _append(self, text: str):
        """Append *text* to the chat box and auto-scroll to the bottom."""
        self.chat_box.config(state="normal")
        self.chat_box.insert("end", text + "\n\n")
        self.chat_box.see("end")  # auto-scroll
        self.chat_box.config(state="disabled")

    def _set_status(self, text: str, fg: str | None = None):
        """Update the status label text and optionally its colour."""
        self.status_label.config(text=text, fg=fg or self.FG_COLOR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    ChatGUI(root)
    root.mainloop()
