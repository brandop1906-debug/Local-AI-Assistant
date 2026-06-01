"""
launcher.py
===========
A Tkinter-based launcher for the Local AI Assistant modules.

Loads module definitions from config.json and displays them as clickable
buttons in a clean, modern GUI. Clicking a button launches the module's
Python file using subprocess (no cloud APIs required).

Requirements:
  - Python 3.6+
  - config.json in the same directory
  - No external dependencies (uses only built-in libraries)

Usage:
  python launcher.py
  (or double-click launcher.py on Windows)
"""

import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# App metadata (shown in the window title and footer)
APP_NAME = "Local AI Assistant"
APP_FOOTER = "Powered by Local AI \u2014 No Cloud"


# ---------------------------------------------------------------------------
# Config loading helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """
    Load and validate config.json.

    Returns:
        A dictionary with the parsed config, or a minimal fallback if
        the file is missing or malformed.

    Raises:
        (Never raises -- errors are caught and displayed gracefully.)
    """
    # Default fallback config (used if config.json is missing/broken)
    fallback = {
        "app_name": APP_NAME,
        "modules": [],
    }

    if not os.path.isfile(CONFIG_PATH):
        return fallback

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        messagebox.showwarning(
            "Config Error",
            f"config.json could not be parsed:\n{e}\n\n"
            f"Using a blank launcher. Please check the JSON syntax."
        )
        return fallback
    except OSError as e:
        messagebox.showwarning(
            "Config Error",
            f"config.json could not be read:\n{e}\n\n"
            f"Using a blank launcher."
        )
        return fallback

    # Validate that the config has the expected structure
    if not isinstance(config, dict):
        messagebox.showwarning(
            "Config Error",
            "config.json must be a JSON object (top-level {})."
        )
        return fallback

    # Ensure 'modules' key exists and is a list
    modules = config.get("modules", [])
    if not isinstance(modules, list):
        messagebox.showwarning(
            "Config Error",
            "The 'modules' key in config.json must be a list."
        )
        modules = []

    # Validate each module entry
    valid_modules = []
    for i, mod in enumerate(modules):
        if not isinstance(mod, dict):
            print(f"[WARN] Module entry #{i + 1} is not a JSON object -- skipping.")
            continue
        name = mod.get("name")
        path = mod.get("path")
        if not name:
            print(f"[WARN] Module entry #{i + 1} is missing 'name' -- skipping.")
            continue
        if not path:
            print(f"[WARN] Module entry for '{name}' is missing 'path' -- skipping.")
            continue
        valid_modules.append({"name": name, "path": path})

    # Return the validated config
    return {
        "app_name": config.get("app_name", APP_NAME),
        "modules": valid_modules,
    }


# ---------------------------------------------------------------------------
# Module launcher
# ---------------------------------------------------------------------------

def launch_module(module_path: str) -> None:
    """
    Launch a module's Python file using subprocess.

    On Windows, the file is opened with the default Python interpreter
    so non-technical users don't need to type 'python' on the command line.

    Args:
        module_path: The relative path to the module's main Python file
                     (relative to the project root / SCRIPT_DIR).
    """
    # Resolve the full path (relative to the project directory)
    full_path = os.path.join(SCRIPT_DIR, module_path)

    # Check the file exists before trying to launch
    if not os.path.isfile(full_path):
        messagebox.showerror(
            "Module Not Found",
            f"Could not find the module file:\n\n{full_path}\n\n"
            f"Please check that the file exists and that the 'path' in\n"
            f"config.json is correct."
        )
        return

    try:
        # On Windows, use 'python' explicitly to avoid association issues.
        # This works regardless of whether Python is in the system PATH.
        subprocess.Popen(
            [sys.executable, full_path],
            cwd=SCRIPT_DIR,
            # Hide the console window on Windows for a cleaner experience.
            # Set to None if you want to see console output for debugging.
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except FileNotFoundError:
        messagebox.showerror(
            "Python Not Found",
            f"Python could not be found on this system.\n\n"
            f"Please install Python 3.6+ and ensure it is in your PATH.\n\n"
            f"Download: https://python.org/downloads"
        )
    except Exception as e:
        messagebox.showerror(
            "Launch Error",
            f"Failed to launch the module:\n\n{full_path}\n\n"
            f"Error: {e}"
        )


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

class LauncherApp:
    """Main launcher application window."""

    # Color palette (subtle, modern, professional)
    COLORS = {
        "bg":            "#f5f6fa",       # Light gray background
        "card_bg":       "#ffffff",       # White card background
        "card_border":   "#e1e5eb",       # Card border
        "btn_bg":        "#4a90d9",       # Blue button
        "btn_fg":        "#ffffff",       # White text
        "btn_hover":     "#3a7bc8",       # Hover state
        "btn_disabled":  "#b0b8c4",       # Disabled state
        "footer_fg":     "#8a93a6",       # Footer text
        "title_fg":      "#2c3e50",       # Title text
        "subtitle_fg":   "#7f8c9b",       # Subtitle text
        "error_fg":      "#e74c3c",       # Error text
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("520x580")
        self.root.minsize(400, 450)
        self.root.resizable(True, True)

        # Load configuration
        self.config = load_config()
        self.app_name = self.config.get("app_name", APP_NAME)
        self.modules = self.config.get("modules", [])

        # Build the UI
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        """Configure the root window styling."""
        # Set a subtle background color
        self.root.configure(bg=self.COLORS["bg"])

        # Set a nice icon if available (Windows)
        icon_path = os.path.join(SCRIPT_DIR, "assets", "icon.png")
        if os.path.isfile(icon_path):
            try:
                self.root.iconbitmap(os.path.abspath(icon_path))
            except tk.TclError:
                pass  # iconbitmap doesn't accept .png on all systems

    def _build_ui(self) -> None:
        """Build the full GUI layout."""
        # ---- Top padding (empty space at the top) ----
        tk.Frame(self.root, height=20).pack(fill=tk.X)

        # ---- Title ----
        title = tk.Label(
            self.root,
            text=self.app_name,
            font=("Segoe UI", 22, "bold"),
            fg=self.COLORS["title_fg"],
            bg=self.COLORS["bg"],
        )
        title.pack(pady=(0, 6))

        # ---- Subtitle ----
        subtitle = tk.Label(
            self.root,
            text="Choose a module to get started",
            font=("Segoe UI", 11),
            fg=self.COLORS["subtitle_fg"],
            bg=self.COLORS["bg"],
        )
        subtitle.pack(pady=(0, 20))

        # ---- Module buttons (in a scrollable card container) ----
        if not self.modules:
            # No modules configured -- show a helpful message
            self._build_empty_state()
        else:
            self._build_module_cards()

        # ---- Bottom padding ----
        tk.Frame(self.root, height=10).pack(fill=tk.X)

        # ---- Footer ----
        footer = tk.Label(
            self.root,
            text=APP_FOOTER,
            font=("Segoe UI", 9),
            fg=self.COLORS["footer_fg"],
            bg=self.COLORS["bg"],
        )
        footer.pack(pady=(0, 15))

    def _build_empty_state(self) -> None:
        """Show a message when no modules are configured."""
        card = tk.Frame(
            self.root,
            bg=self.COLORS["card_bg"],
            relief=tk.RAISED,
            borderwidth=1,
        )
        card.pack(fill=tk.X, padx=30, expand=True)
        card.configure(width=460)
        card.update()  # Ensure width is set before packing

        msg = tk.Label(
            card,
            text=(
                "No modules configured.\n\n"
                "Add modules to config.json like this:\n\n"
                '  {\n'
                '    "name": "My Module",\n'
                '    "path": "modules/my_module/gui.py"\n'
                '  }'
            ),
            font=("Segoe UI", 10),
            fg=self.COLORS["error_fg"],
            bg=self.COLORS["card_bg"],
            wraplength=400,
            justify=tk.CENTER,
        )
        msg.pack(pady=30, padx=20)

    def _build_module_cards(self) -> None:
        """Build a card-style button for each configured module."""
        # Container frame with padding
        container = tk.Frame(self.root, bg=self.COLORS["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=30)

        # Create a canvas + scrollbar for scrolling if there are many modules
        canvas = tk.Canvas(
            container,
            bg=self.COLORS["bg"],
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview,
        )
        self.scrollable_frame = tk.Frame(canvas, bg=self.COLORS["bg"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel to scroll on Windows
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Build a button card for each module
        for i, module in enumerate(self.modules):
            self._create_module_card(module, i)

    def _create_module_card(self, module: dict, index: int) -> None:
        """
        Create a single module card (button) with hover effects.

        Args:
            module: A dict with 'name' and 'path' keys.
            index:  The 0-based index (used for alternating colors).
        """
        name = module["name"]
        path = module["path"]

        # Alternate subtle background for visual separation
        bg_color = self.COLORS["card_bg"] if index % 2 == 0 else "#f9fafc"

        card = tk.Frame(
            self.scrollable_frame,
            bg=self.COLORS["card_border"],
            relief=tk.RAISED,
            borderwidth=1,
        )
        card.pack(fill=tk.X, pady=(4, 0))
        card.configure(width=460)
        card.update()

        # Inner frame (the actual clickable area)
        inner = tk.Frame(card, bg=bg_color)
        inner.pack(fill=tk.X, padx=2, pady=2)
        inner.configure(width=456)
        inner.update()

        # Module name label
        name_label = tk.Label(
            inner,
            text=f"\u25B6  {name}",
            font=("Segoe UI", 12, "bold"),
            fg=self.COLORS["title_fg"],
            bg=bg_color,
            anchor=tk.W,
        )
        name_label.pack(side=tk.LEFT, padx=15, pady=10, fill=tk.X, expand=True)

        # Launch button
        btn = tk.Button(
            inner,
            text="Launch",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLORS["btn_fg"],
            bg=self.COLORS["btn_bg"],
            activebackground=self.COLORS["btn_hover"],
            activeforeground=self.COLORS["btn_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            width=10,
            command=lambda p=path: self._on_launch(p),
        )
        btn.pack(side=tk.RIGHT, padx=(0, 15), pady=6)

        # Hover effects
        def _on_enter(event):
            btn.config(bg=self.COLORS["btn_hover"])

        def _on_leave(event):
            btn.config(bg=self.COLORS["btn_bg"])

        btn.bind("<Enter>", _on_enter)
        btn.bind("<Leave>", _on_leave)

    def _on_launch(self, module_path: str) -> None:
        """Handle the Launch button click."""
        launch_module(module_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Create and run the launcher application."""
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Launcher closed.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERR] Launcher failed to start: {e}")
        sys.exit(1)
