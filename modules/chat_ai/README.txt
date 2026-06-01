chat_ai module
================
Project-aware chat module for the Local AI Assistant.

FEATURES
--------
- Asks a local LLM (via LM Studio) and returns responses
- Automatically injects project context (pricing, FAQs, modules, docs)
- Tkinter GUI with "Thinking..." status indicator
- CLI test mode for quick debugging

USAGE
-----
1. As a module:
   from chat_ai.chat import ask_ai
   response = ask_ai("What is your pricing?")

2. As a CLI:
   python chat.py "What is your pricing?"

3. As a GUI:
   python gui.py

PROJECT CONTEXT
---------------
The chatbot now "knows" about your project because:
- It reads your business_brain/documents/ files (FAQs, pricing, policies)
- It scans the launcher config for all module names/paths
- It includes README files from the project

This means asking "What's your pricing?" will return accurate info
from your service_pricing.txt file instead of a generic answer.

CONFIGURATION
-------------
Edit modules/chat_ai/config.json:
  - model: Which LM Studio model to use
  - system_prompt: AI's personality/role
  - temperature: Creativity (0.0-1.0)
  - max_tokens: Max response length
  - api_url: LM Studio server URL (default: localhost:1234)

TROUBLESHOOTING
---------------
- "ModuleNotFoundError": Run from the project root, not inside chat_ai/
- Garbled text (e.g., "Iâ€™ll"): Ensure Windows terminal is UTF-8
  (Run: chcp 65001 in cmd, or set PYTHONIOENCODING=utf-8)
- "curl failed": Make sure LM Studio is running with a model loaded
- Context too large: The builder automatically truncates to 8000 tokens
