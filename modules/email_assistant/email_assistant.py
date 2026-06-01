"""
email_assistant.py
==================
A local, offline email drafting assistant powered by LM Studio.

This script:
  1. Lets you describe the email you want to write
  2. Lets you pick a tone via dropdown (professional, friendly, urgent)
  3. Loads the matching tone template from /templates
  4. Sends the combined prompt to LM Studio's local server
  5. Displays the polished email with a "Copy to Clipboard" button
  6. Saves the email to /output with a timestamp

No cloud APIs required. Everything runs on your machine.

Requirements:
  - Python 3.6+
  - LM Studio installed and running: https://lmstudio.ai
  - A model loaded in LM Studio with the Local Server started

Usage:
  python email_assistant.py
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

# Force UTF-8 encoding on Windows
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# LM Studio uses the requests library for HTTP calls.
# If you don't have it, run: pip install requests
try:
    import requests
except ImportError:
    # Fallback: use urllib (built-in, no pip install needed)
    import urllib.request
    import urllib.error


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
    "temperature": 0.7,
    "max_tokens": 2048,
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


def load_template(tone: str) -> str:
    """
    Load the tone template file from /templates.

    Args:
        tone: One of 'professional', 'friendly', or 'urgent'

    Returns:
        The template text as a string.
    """
    template_path = os.path.join(TEMPLATES_DIR, f"{tone}.txt")
    if not os.path.isfile(template_path):
        raise FileNotFoundError(
            f"Template not found: {template_path}\n"
            f"Please create a '{tone}.txt' file in the 'templates' folder."
        )
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def ask_user(question: str) -> str:
    """
    Print a question and return the user's trimmed input.

    Args:
        question: The question to display.

    Returns:
        The user's input as a string.
    """
    return input(question).strip()


def print_banner() -> None:
    """Print a simple welcome banner."""
    print()
    print("=" * 60)
    print("       [EMAIL] Email Assistant (powered by LM Studio)")
    print("=" * 60)
    print()


def save_email(content: str) -> str:
    """
    Save the email content to /output with a timestamped filename.

    Args:
        content: The email text to save.

    Returns:
        The full path to the saved file.
    """
    ensure_dir(OUTPUT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"email_{timestamp}.txt"
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
        # Fallback: urllib
        import urllib.request
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
                f"Cannot connect to LM Studio at {LM_STUDIO_HOST}.\\n"
                f"Please make sure:\\n"
                f"  1. LM Studio is running\\n"
                f"  2. A model is loaded\\n"
                f"  3. The Local Server is started (bottom-left icon)\\n"
                f"  4. The port matches LM_STUDIO_HOST (default: 1234)"
            )
        # Parse the urllib response manually
        try:
            data = json.loads(response_text)
            return data["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(
                f"LM Studio returned unexpected data:\\n{response_text}\\n"
                f"Error: {e}"
            )

    # Parse the requests response
    if response.status_code != 200:
        raise RuntimeError(
            f"LM Studio returned status {response.status_code}:\\n{response.text}"
        )

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raise RuntimeError(
            f"LM Studio returned unexpected data:\\n{response.text}\\nError: {e}"
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

TONES = ["professional", "friendly", "urgent"]


class EmailAssistantGUI:
    """Tkinter-based GUI for the email drafting assistant."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Email Assistant (LM Studio)")
        self.root.geometry("700x600")
        self.root.minsize(500, 450)
        self._build_ui()

        # Check LM Studio on startup (non-blocking, shown in status bar)
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
            text="✉  Email Assistant",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # ---- Email description (text box) ----
        desc_label = ttk.Label(main_frame, text="Describe the email you want to write:")
        desc_label.pack(anchor=tk.W)

        self.desc_text = scrolledtext.ScrolledText(
            main_frame,
            height=6,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        self.desc_text.pack(fill=tk.X, pady=(2, 10))
        self.desc_text.insert(tk.END, "e.g., Follow up with a client about the pending invoice")
        self.desc_text.bind("<FocusIn>", self._on_desc_focus_in)

        # ---- Tone selection (dropdown) ----
        tone_frame = ttk.Frame(main_frame)
        tone_frame.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(tone_frame, text="Tone:").pack(side=tk.LEFT, padx=(0, 10))

        self.tone_var = tk.StringVar(value="professional")
        self.tone_combo = ttk.Combobox(
            tone_frame,
            values=TONES,
            textvariable=self.tone_var,
            state="readonly",
            width=20,
        )
        self.tone_combo.pack(side=tk.LEFT)

        # ---- Generate button ----
        self.generate_btn = ttk.Button(
            main_frame,
            text="⚡ Generate Email",
            command=self._generate,
        )
        self.generate_btn.pack(pady=(5, 10))

        # ---- Result area ----
        result_frame = ttk.LabelFrame(main_frame, text="Generated Email", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=10,
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
        if self.desc_text.get(1.0, tk.END).strip() == "e.g., Follow up with a client about the pending invoice":
            self.desc_text.delete(1.0, tk.END)

    def _generate(self) -> None:
        """Generate the email based on user input."""
        email_topic = self.desc_text.get(1.0, tk.END).strip()
        if not email_topic:
            messagebox.showerror("Error", "Please describe the email you want to write.")
            return

        tone = self.tone_var.get()

        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("Generating email... Please wait.")
        self.root.update()

        try:
            # Load template
            template_text = load_template(tone)

            # Build prompt
            full_prompt = (
                f"{template_text}\n\n"
                f"Email topic / summary:\n{email_topic}\n\n"
                f"Please write the complete email based on the topic above.\n"
                f"Include a subject line and the email body."
            )

            # Call LM Studio
            email_content = call_lm_studio(full_prompt)

            # Save to file
            filepath = save_email(email_content)

            # Display result
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, email_content)
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
        finally:
            self.generate_btn.config(state=tk.NORMAL)

    def _copy_to_clipboard(self) -> None:
        """Copy the generated email to the clipboard."""
        email_content = self.result_text.get(1.0, tk.END).strip()
        if email_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(email_content)
            self.status_var.set("Copied to clipboard!")
            messagebox.showinfo("Copied", "Email has been copied to your clipboard.")

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
    """Run the email assistant with a Tkinter GUI."""
    root = tk.Tk()
    app = EmailAssistantGUI(root)
    root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Interrupted by user. Goodbye.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERR] An unexpected error occurred: {e}")
        sys.exit(1)
