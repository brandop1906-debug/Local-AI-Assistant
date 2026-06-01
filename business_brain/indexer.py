"""
Indexer: Scans documents and builds searchable embeddings.
"""

import os
import json
import hashlib


def index_documents(documents_dir: str) -> dict:
    """Scan the documents directory and return an index of all files."""
    index = {}

    for root, _, files in os.walk(documents_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, documents_dir)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            index[relpath] = {
                "path": filepath,
                "hash": hashlib.md5(content.encode()).hexdigest(),
                "content": content,
            }

    return index


def save_index(index: dict, output_path: str):
    """Save the index to disk."""
    # Strip internal 'content' keys before saving
    save_data = {k: {kk: vv for kk, vv in v.items() if kk != "content"} for k, v in index.items()}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)


if __name__ == "__main__":
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")
    output_path = os.path.join(os.path.dirname(__file__), "embeddings.json")
    index = index_documents(docs_dir)
    save_index(index, output_path)
    print(f"Indexed {len(index)} documents -> {output_path}")
