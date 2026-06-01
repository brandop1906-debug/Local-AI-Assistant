"""
gui.py — Simple Tkinter GUI for querying the Business Brain.
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

from ask_brain import ask, display_results


def main():
    root = tk.Tk()
    root.title("Business Brain")
    root.geometry("800x550")

    # --- Top bar: query input ---
    top_frame = ttk.Frame(root)
    top_frame.pack(fill="x", padx=10, pady=8)

    query_var = tk.StringVar()
    ttk.Label(top_frame, text="Query:").pack(side="left", padx=(0, 6))
    ttk.Entry(top_frame, textvariable=query_var, width=55).pack(side="left", fill="x", expand=True, padx=(0, 6))

    use_semantic = tk.BooleanVar(value=True)
    ttk.Checkbutton(top_frame, text="Semantic (Ollama)", variable=use_semantic).pack(side="left", padx=(0, 6))

    def on_search():
        query = query_var.get().strip()
        if not query:
            messagebox.showwarning("No query", "Please enter a search term.")
            return
        results = ask(query, use_semantic=use_semantic.get())
        results_text.delete(1.0, tk.END)
        display_results(results)

    ttk.Button(top_frame, text="Search", command=on_search).pack(side="left")

    # --- Results pane ---
    results_text = scrolledtext.ScrolledText(root, width=90, height=25, state="disabled")
    results_text.pack(padx=10, pady=5, fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
