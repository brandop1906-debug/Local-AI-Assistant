"""
quote_generator.py
==================
A local, offline service quote generator powered by LM Studio.

This script:
  1. Asks you to describe the services you need a quote for
  2. Loads a base quote template from /templates
  3. Combines the template with your description
  4. Sends the combined prompt to LM Studio's local server
  5. Displays the polished, formatted service quote
  6. Saves the quote to /output with a timestamped filename

No cloud APIs required. Everything runs on your machine.

Requirements:
  - Python 3.6+
  - LM Studio installed and running: https://lmstudio.ai
  - A model loaded in LM Studio with the Local Server started

Usage:
  python quote_generator.py
  (or double-click run.bat on Windows)
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

# ---------------------------------------------------------------------------
# Force UTF-8 encoding on Windows so characters display correctly
# ---------------------------------------------------------------------------
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Configuration – loads from config.json, falls back to defaults
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# Sensible defaults (used when config.json is missing or invalid)
DEFAULT_CONFIG = {
    "model": "qwen/qwen3.6-35b-a3b",
    "lm_studio_host": "http://127.0.0.1:1234",
    "output_folder": "output",
    "template_folder": "templates",
    "temperature": 0.5,
    "max_tokens": 3072,
}


def load_config() -> dict:
    """
    Load configuration from config.json, with environment variable overrides.

    Priority (highest to lowest):
      1. Environment variables (e.g. LM_STUDIO_HOST)
      2. config.json values
      3. DEFAULT_CONFIG fallbacks

    Returns:
        A config dictionary.
    """
    config = dict(DEFAULT_CONFIG)

    # 1. Load from config.json if it exists
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            if isinstance(file_config, dict):
                # Only accept known keys to avoid surprises
                for key in DEFAULT_CONFIG:
                    if key in file_config:
                        config[key] = file_config[key]
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Failed to load {CONFIG_PATH}: {e}. Using defaults.")

    # 2. Environment variable overrides (highest priority)
    env_host = os.environ.get("LM_STUDIO_HOST")
    if env_host:
        config["lm_studio_host"] = env_host

    env_model = os.environ.get("LM_STUDIO_MODEL")
    if env_model:
        config["model"] = env_model

    env_temp = os.environ.get("LM_TEMPERATURE")
    if env_temp is not None:
        try:
            config["temperature"] = float(env_temp)
        except ValueError:
            pass

    env_max = os.environ.get("LM_MAX_TOKENS")
    if env_max is not None:
        try:
            config["max_tokens"] = int(env_max)
        except ValueError:
            pass

    return config


# Load config at module import time
CONFIG = load_config()

# Expose as module-level variables for backward compatibility
LM_STUDIO_MODEL = CONFIG["model"]
LM_STUDIO_HOST = CONFIG["lm_studio_host"]
LM_TEMPERATURE = CONFIG["temperature"]
LM_MAX_TOKENS = CONFIG["max_tokens"]
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, CONFIG["template_folder"])
OUTPUT_DIR = os.path.join(SCRIPT_DIR, CONFIG["output_folder"])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """Create the directory if it doesn't exist (silent if it does)."""
    os.makedirs(path, exist_ok=True)


def load_template(name: str = "quote_base") -> str:
    """
    Load a template file from /templates.

    Args:
        name: The template filename (without .txt extension).

    Returns:
        The template text as a string.
    """
    template_path = os.path.join(TEMPLATES_DIR, f"{name}.txt")
    if not os.path.isfile(template_path):
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Please create a '{name}.txt' file in the 'templates' folder."
        )
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def print_banner() -> None:
    """Print a simple welcome banner."""
    print()
    print("=" * 60)
    print("       [QUOTE] Service Quote Generator (LM Studio)")
    print("=" * 60)
    print()


def save_quote(content: str) -> str:
    """
    Save the quote content to /output with a timestamped filename.

    Args:
        content: The quote text to save.

    Returns:
        The full path to the saved file.
    """
    ensure_dir(OUTPUT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"quote_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def call_lm_studio(prompt: str) -> str:
    """
    Send a prompt to LM Studio's local OpenAI-compatible API.

    Args:
        prompt: The full prompt string to send to LM Studio.

    Returns:
        The model's response as a string.

    Raises:
        RuntimeError: If LM Studio is not running or returns an error.
    """
    # Build the OpenAI-compatible chat request
    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": LM_TEMPERATURE,
        "max_tokens": LM_MAX_TOKENS,
        "stream": False,
    }

    url = f"{LM_STUDIO_HOST}/v1/chat/completions"

    # Try using requests first, fall back to urllib
    try:
        import requests
        response = requests.post(url, json=payload, timeout=120)
    except ImportError:
        # Fallback: urllib (built-in, no pip install needed)
        import urllib.request
        import urllib.error

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_text = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to LM Studio at {LM_STUDIO_HOST}.\n"
                f"Please make sure:\n"
                f"  1. LM Studio is running\n"
                f"  2. A model is loaded\n"
                f"  3. The Local Server is started (bottom-left icon)\n"
                f"  4. The port matches LM_STUDIO_HOST (default: 1234)"
            )
        # Parse the urllib response manually
        try:
            data = json.loads(response_text)
            return data["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(
                f"LM Studio returned unexpected data:\n{response_text}\n"
                f"Error: {e}"
            )

    # Parse the requests response
    if response.status_code != 200:
        raise RuntimeError(
            f"LM Studio returned status {response.status_code}:\n{response.text}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise RuntimeError(
            f"LM Studio returned unexpected data:\n{response.text}\nError: {e}"
        )


def check_lm_studio() -> bool:
    """
    Check if LM Studio's local server is reachable.

    Tries multiple endpoints in order of reliability:
      1. /v1/models       – OpenAI-compatible models list
      2. /health          – Simple health ping
      3. Root /           – Bare connection test

    Returns:
        True if the server responds, False otherwise.
    """
    endpoints = [
        f"{LM_STUDIO_HOST}/v1/models",
        f"{LM_STUDIO_HOST}/health",
        f"{LM_STUDIO_HOST}/",
    ]

    # Try requests first (preferred)
    try:
        import requests
        for url in endpoints:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False
    except ImportError:
        pass

    # Fallback: urllib
    try:
        import urllib.request
        for url in endpoints:
            try:
                resp = urllib.request.urlopen(url, timeout=10)
                if resp.status == 200:
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------


class QuoteGeneratorGUI:
    """Tkinter-based GUI for the service quote generator."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Service Quote Generator (LM Studio)")
        self.root.geometry("750x650")
        self.root.minsize(550, 500)
        self._build_ui()

        # Check LM Studio on startup
        self.lm_studio_ok = check_lm_studio()
        if not self.lm_studio_ok:
            self.status_var.set(
                "⚠ LM Studio not detected — make sure it's running with the Local Server started"
            )

    def _build_ui(self) -> None:
        """Construct the GUI layout."""
        # ---- Main frame with padding ----
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Title ----
        title_label = ttk.Label(
            main_frame,
            text="📋  Service Quote Generator",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # ---- Subtitle / instructions ----
        subtitle = ttk.Label(
            main_frame,
            text="Describe the services you need a quote for, then click Generate.",
            font=("Segoe UI", 9),
            foreground="gray",
        )
        subtitle.pack(pady=(0, 15))

        # ---- Services description (text box) ----
        desc_label = ttk.Label(main_frame, text="Services / Project Description:")
        desc_label.pack(anchor=tk.W)

        self.desc_text = scrolledtext.ScrolledText(
            main_frame,
            height=7,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        self.desc_text.pack(fill=tk.X, pady=(2, 10))
        self.desc_text.insert(
            tk.END,
            "e.g., Home office electrical wiring for a 12x10 room, "
            "including outlet installation, switch wiring, and ceiling light fixture. "
            "Client prefers daytime work and needs materials included.",
        )
        self.desc_text.bind("<FocusIn>", self._on_desc_focus_in)

        # ---- Generate button ----
        self.generate_btn = ttk.Button(
            main_frame,
            text="⚡ Generate Quote",
            command=self._generate,
        )
        self.generate_btn.pack(pady=(5, 10))

        # ---- Result area ----
        result_frame = ttk.LabelFrame(main_frame, text="Generated Quote", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=12,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # ---- Action buttons ----
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)

        self.copy_btn = ttk.Button(
            action_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard,
            state=tk.DISABLED,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.open_btn = ttk.Button(
            action_frame,
            text="📂 Open Output Folder",
            command=self._open_output_folder,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _on_desc_focus_in(self, event: tk.Event) -> None:
        """Clear placeholder text on focus."""
        placeholder = (
            "e.g., Home office electrical wiring for a 12x10 room, "
            "including outlet installation, switch wiring, and ceiling light fixture. "
            "Client prefers daytime work and needs materials included."
        )
        if self.desc_text.get(1.0, tk.END).strip() == placeholder:
            self.desc_text.delete(1.0, tk.END)

    def _generate(self) -> None:
        """Generate the quote based on user input."""
        services_desc = self.desc_text.get(1.0, tk.END).strip()
        if not services_desc:
            messagebox.showerror("Error", "Please describe the services you need a quote for.")
            return

        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("Generating quote... Please wait.")
        self.root.update()

        try:
            # Load template
            template_text = load_template("quote_base")

            # Build prompt: template + user's service description
            full_prompt = (
                f"{template_text}\n\n"
                f"Services / project description:\n{services_desc}\n\n"
                f"Please generate a complete, professional service quote based on the description above.\n"
                f"Include all standard sections: header, scope of work, pricing, terms, and contact info."
            )

            # Call LM Studio
            quote_content = call_lm_studio(full_prompt)

            # Save to file
            filepath = save_quote(quote_content)

            # Display result
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, quote_content)
            self.result_text.config(state=tk.DISABLED)

            self.copy_btn.config(state=tk.NORMAL)
            self.open_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Done! Saved to: {filepath}")

        except RuntimeError as e:
            self.status_var.set("Error")
            messagebox.showerror("LM Studio Error", str(e))
        except FileNotFoundError as e:
            self.status_var.set("Error")
            messagebox.showerror("Template Error", str(e))
        except Exception as e:
            self.status_var.set("Error")
            messagebox.showerror("Unexpected Error", str(e))
        finally:
            self.generate_btn.config(state=tk.NORMAL)

    def _copy_to_clipboard(self) -> None:
        """Copy the generated quote to the clipboard."""
        quote_content = self.result_text.get(1.0, tk.END).strip()
        if quote_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(quote_content)
            self.status_var.set("Copied to clipboard!")
            messagebox.showinfo("Copied", "Quote has been copied to your clipboard.")

    def _open_output_folder(self) -> None:
        """Open the output folder in the file explorer."""
        ensure_dir(OUTPUT_DIR)
        if sys.platform == "win32":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            os.system(f"open {OUTPUT_DIR}")
        else:
            os.system(f"xdg-open {OUTPUT_DIR}")


def main() -> None:
    """Run the quote generator with a Tkinter GUI."""
    root = tk.Tk()
    app = QuoteGeneratorGUI(root)
    root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        print_banner()
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Interrupted by user. Goodbye.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERR] An unexpected error occurred: {e}")
        sys.exit(1)
