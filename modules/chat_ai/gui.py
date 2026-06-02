"""
chat_ai/gui.py
==============
CustomTkinter GUI for the Local AI Assistant chat module.

Displays a conversation log, accepts user input, and calls
chat.ask_ai() to get responses from the local LM Studio model.

Run with:
    python gui.py
    (or launch from launcher.py)
"""

import os
import customtkinter as ctk
import threading

from modules.chat_ai.chat import ask_ai

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


class ChatGUI:
    """Modern CustomTkinter chat window backed by the local LM Studio model."""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Local AI Assistant — Chat")
        self.root.geometry("750x700")
        self.root.minsize(420, 600)

        # Dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._is_responding = False
        self._build_ui()

    def _build_ui(self):
        self.root.configure(fg_color=DARK_BG)

        # ---- Top accent bar ----
        accent_bar = ctk.CTkFrame(self.root, fg_color=ACCENT, height=3)
        accent_bar.pack(fill="x", side="top")
        accent_bar.pack_propagate(False)

        # ---- Chat history area ----
        self.chat_frame = ctk.CTkScrollableFrame(
            self.root,
            fg_color=DARK_BG,
            border_color=DARK_BG,
        )
        self.chat_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # ---- Status bar ----
        self.status_label = ctk.CTkLabel(
            self.root,
            text="Ready",
            font=(FONT_FAMILY, 10),
            text_color=GRAY,
        )
        self.status_label.pack(fill="x", padx=12, pady=(0, 4))

        # ---- Bottom input bar ----
        self._build_input_bar()

    def _build_input_bar(self):
        input_frame = ctk.CTkFrame(
            self.root,
            fg_color=DARK_SURFACE,
            corner_radius=16,
            border_width=1,
            border_color=DARK_BORDER,
        )
        input_frame.pack(fill="x", padx=12, pady=(0, 12))
        input_frame.configure(height=56)
        input_frame.pack_propagate(False)

        self.entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message...",
            font=(FONT_FAMILY, 13),
            text_color=WHITE,
            placeholder_text_color=GRAY,
            fg_color=DARK_INPUT,
            corner_radius=12,
            height=40,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=8)
        self.entry.bind("<Return>", self._on_send)

        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=ACCENT,
            hover_color="#5ba0e9",
            text_color=WHITE,
            corner_radius=12,
            width=72,
            height=40,
            command=self._on_send,
        )
        self.send_btn.pack(side="right", padx=(0, 8), pady=8)

    def _on_send(self, _event=None):
        """Handle Send button click or Enter key press."""
        if self._is_responding:
            return

        message = self.entry.get().strip()
        if not message:
            return

        self.entry.delete(0, "end")
        self._append_message("You", message, is_user=True)

        self._is_responding = True
        self._set_status("Thinking...", fg=YELLOW)
        self.entry.configure(state="disabled")
        self.send_btn.configure(state="disabled")

        thread = threading.Thread(target=self._handle_response, args=(message,), daemon=True)
        thread.start()

    def _handle_response(self, user_message: str):
        """Background thread: call ask_ai() and update the GUI on return."""
        response = None
        error_msg = None
        try:
            response = ask_ai(user_message)
        except Exception as exc:
            error_msg = str(exc)
            import traceback
            traceback.print_exc()

        self.root.after(0, self._finalize_response, response, error_msg)

    def _finalize_response(self, response: str | None, error_msg: str | None):
        """Restore UI state and display the result."""
        self._is_responding = False
        self.entry.configure(state="normal")
        self.entry.focus()
        self.send_btn.configure(state="normal")

        if response is not None:
            self._append_message("AI", response, is_user=False)
            self._set_status("Ready", fg=GRAY)
        else:
            display_msg = error_msg or "No response received. Is LM Studio running?"
            self._append_message("Error", display_msg, is_user=False, is_error=True)
            self._set_status("Error", fg=RED)

    def _append_message(self, sender: str, text: str, is_user: bool = False, is_error: bool = False):
        """Append a message bubble to the chat."""
        is_error = is_error or sender == "Error"

        # Sender label
        sender_color = ACCENT if is_user else GREEN if sender == "AI" else RED
        sender_label = ctk.CTkLabel(
            self.chat_frame,
            text=sender,
            font=(FONT_FAMILY, 10, "bold"),
            text_color=sender_color,
            anchor="w",
        )
        sender_label.pack(fill="x", padx=4, pady=(8, 0))

        # Message bubble
        bg = DARK_INPUT if is_user else DARK_SURFACE
        border = ACCENT if is_user else DARK_BORDER

        bubble = ctk.CTkFrame(
            self.chat_frame,
            fg_color=bg,
            border_width=1,
            border_color=border,
            corner_radius=14,
        )
        bubble.pack(fill="x", padx=4, pady=2)
        bubble.configure(width=680)
        bubble.update()

        msg_label = ctk.CTkLabel(
            bubble,
            text=text,
            font=(FONT_FAMILY, 12),
            text_color=WHITE if not is_error else RED,
            wraplength=640,
            justify="left",
            anchor="w",
        )
        msg_label.pack(fill="x", padx=14, pady=10)

        # Auto-scroll to bottom
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll the chat frame to the bottom."""
        try:
            # Try CTk 5.x path first
            self.chat_frame.scrollable_frame.canvas.yview_moveto(1.0)
        except AttributeError:
            try:
                # Try direct canvas access (older CTk versions)
                self.chat_frame.canvas.yview_moveto(1.0)
            except AttributeError:
                pass  # Scroll not available, that's OK

    def _set_status(self, text: str, fg: str = GRAY):
        """Update the status label."""
        self.status_label.configure(text=text, text_color=fg)

    def _on_clear(self):
        """Clear the conversation history."""
        # Remove all child widgets from the chat frame
        for child in self.chat_frame.winfo_children():
            child.destroy()
        self._set_status("Ready", fg=GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = ctk.CTk()
    ChatGUI(root)
    root.mainloop()
