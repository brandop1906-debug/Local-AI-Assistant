"""
chat_ai package
===============
Local AI Assistant chat module.

Provides:
    - chat.ask_ai(): Send a message to the local LLM
    - context.build_project_context(): Build project-aware context
    - gui.ChatGUI: Tkinter chat interface
"""

from chat_ai.chat import ask_ai
from chat_ai.context import build_project_context, inject_context

__all__ = ["ask_ai", "build_project_context", "inject_context"]
__version__ = "1.0.0"
