# chat_ai — Local AI Chat Module

A chat module for the Local AI Assistant that communicates with LM Studio's local API server — no cloud APIs required.

## Features

### RAG (Retrieval-Augmented Generation)

Instead of dumping all documents into the prompt, `chat_ai` now uses **semantic search** to retrieve only the most relevant chunks for each query. This is much more efficient and scalable.

**How RAG works:**

1. User asks a question
2. The question is embedded using the same model as `business_brain` (e.g. `nomic-embed-text`)
3. Cosine similarity finds the top-K most relevant document chunks
4. Only those chunks are injected into the system prompt
5. The LLM answers using the retrieved context

### Quick Start

```python
from chat_ai import ask_ai

# Simple chat
response = ask_ai("What is the pricing structure?")
print(response)

# With context disabled (faster, no document retrieval)
response = ask_ai("Hello!", include_context=False)
```

### CLI Test

```bash
python -m chat_ai.chat "What is the pricing structure?"
```

## Configuration

Edit `config.json`:

```json
{
  "model": "qwen:7b",
  "system_prompt": "You are a helpful business assistant.",
  "temperature": 0.7,
  "max_tokens": 2048,
  "api_url": "http://localhost:1234/v1/chat/completions",
  "rag_enabled": true,
  "rag_top_k": 5,
  "rag_max_context_chars": 6000
}
```

### RAG Settings

| Key | Default | Description |
|-----|---------|-------------|
| `rag_enabled` | `true` | Enable/disable RAG retrieval |
| `rag_top_k` | `5` | Number of relevant chunks to retrieve |
| `rag_max_context_chars` | `6000` | Max character budget for retrieved context |

## Requirements

- LM Studio running locally with an embedding model (e.g. `nomic-embed-text`) and a chat model (e.g. `qwen:7b`)
- Python 3.10+

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  User    │────▶│   chat_ai    │────▶│  LM Studio   │
│  Query   │     │  (RAG)       │     │  (Local LLM) │
└──────────┘     └──────┬───────┘     └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │business_brain│
                  │embeddings.json│
                  └──────────────┘
```

1. `chat.py` receives the user query
2. `rag.py` embeds the query and searches `business_brain/embeddings.json`
3. Top-K relevant chunks are retrieved via cosine similarity
4. `context.py` injects only those chunks into the system prompt
5. The enriched prompt is sent to LM Studio
6. The LLM answers using the retrieved context

## Module Files

| File | Purpose |
|------|---------|
| `chat.py` | Core ask_ai() function — sends messages to LM Studio |
| `rag.py` | RAG retrieval — semantic search over business_brain index |
| `context.py` | Context building and injection |
| `config.json` | Configuration (model, temperature, RAG settings) |
