"""
chat_ai package
===============
Local AI Assistant chat module.

Provides:
    - chat.ask_ai(): Send a message to the local LLM
    - rag.retriever_context(): Retrieve relevant document chunks (RAG)
    - rag.build_rag_context(): Build RAG-aware context for a query
    - context.build_rag_context(): Build RAG-aware context (convenience import)
    - context.inject_context(): Inject context into system prompt
    - gui.ChatGUI: Tkinter chat interface

RAG (Retrieval-Augmented Generation):
    Instead of dumping all documents into the prompt, chat_ai now uses
    semantic search to retrieve only the most relevant chunks for each
    query. This is much more efficient and scalable.

    from chat_ai.rag import retrieve_context
    chunks = retrieve_context("What is the pricing structure?", top_k=5)
"""

from chat_ai.chat import ask_ai
from chat_ai.context import build_rag_context, inject_context
from chat_ai.rag import semantic_search, retrieve_context, build_rag_context as rag_build_rag_context

__all__ = [
    "ask_ai",
    "build_rag_context",
    "inject_context",
    "semantic_search",
    "retrieve_context",
    "rag_build_rag_context",
]
__version__ = "2.0.0"
