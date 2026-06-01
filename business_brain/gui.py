"""
GUI: A simple Tkinter interface for querying the business brain.
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from ask_brain import ask


def main():
    root = tk.Tk()
    root.title("Business Brain")
    root.geometry("700x500")

    # Query input
    query_var = tk.StringVar()
    ttk.Label(root, text="Query:").pack(pady=(10, 2), anchor="w", padx=10)
    ttk.Entry(root, textvariable=query_var, width=80).pack(padx=10, fill="x")

    def on_search():
        query = query_var.get().strip()
        if not query:
            messagebox.showwarning("No query", "Please enter a search term.")
            return
        results = ask(query)
        results_text.delete(1.0, tk.END)
        if not results:
            results_text.insert(tk.END, "No results found.")
            return
        for relpath, score, content in results:
            results_text.insert(tk.END, f"\n--- {relpath} (score: {score}) ---\n")
            results_text.insert(tk.END, content[:500] + "\n")

    ttk.Button(root, text="Search", command=on_search).pack(pady=5)

    # Results
    results_text = scrolledtext.ScrolledText(root, width=80, height=25, state="disabled")
    results_text.pack(padx=10, pady=5, fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
