"""
launcher.py
===========
A CustomTkinter-based launcher for the Local AI Assistant modules.

Loads module definitions from config.json and displays them as clickable
cards in a sleek, dark-themed GUI. Clicking a button launches the module's
Python file using subprocess (no cloud APIs required).

Requirements:
  - Python 3.6+
  - customtkinter  (pip install customtkinter)
  - config.json in the same directory

Usage:
  python launcher.py
  (or double-click launcher.py on Windows)
"""

import os
import sys
import json
import subprocess
import customtkinter as ctk
from tkinter import messagebox

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

APP_NAME = "Local AI Assistant"
APP_FOOTER = "Powered by Local AI  \u2014  No Cloud"

# Theme colors
THEME = {
    "bg":              "#0f1117",       # Deep dark background
    "card_bg":         "#1a1d27",       # Card background
    "card_hover":      "#222633",       # Card hover
    "card_border":     "#2a2e3a",       # Card border
    "card_border_hover": "#4a90d9",     # Card border on hover
    "accent":          "#4a90d9",       # Primary accent blue
    "accent_hover":    "#5ba0e9",       # Accent hover
    "accent_glow":     "#4a90d940",     # Accent glow
    "btn_bg":          "#4a90d9",       # Button background
    "btn_fg":          "#ffffff",       # Button text
    "btn_hover":       "#5ba0e9",       # Button hover
    "title_fg":        "#e8eaed",       # Title text
    "subtitle_fg":     "#8b8fa3",       # Subtitle text
    "footer_fg":       "#555a6e",       # Footer text
    "error_fg":        "#e74c3c",       # Error text
    "icon_fg":         "#4a90d9",       # Icon/arrow color
}


# ---------------------------------------------------------------------------
# Config loading helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load and validate config.json."""
    fallback = {"app_name": APP_NAME, "modules": []}

    if not os.path.isfile(CONFIG_PATH):
        return fallback

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        messagebox.showwarning("Config Error",
            f"config.json could not be parsed:\n{e}\n\n"
            f"Using a blank launcher. Please check the JSON syntax.")
        return fallback
    except OSError as e:
        messagebox.showwarning("Config Error",
            f"config.json could not be read:\n{e}\n\n"
            f"Using a blank launcher.")
        return fallback

    if not isinstance(config, dict):
        messagebox.showwarning("Config Error",
            "config.json must be a JSON object (top-level {}).")
        return fallback

    modules = config.get("modules", [])
    if not isinstance(modules, list):
        messagebox.showwarning("Config Error",
            "The 'modules' key in config.json must be a list.")
        modules = []

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

    return {"app_name": config.get("app_name", APP_NAME), "modules": valid_modules}


# ---------------------------------------------------------------------------
# Module launcher
# ---------------------------------------------------------------------------

def launch_module(module_path: str) -> None:
    """Launch a module's Python file using subprocess."""
    full_path = os.path.join(SCRIPT_DIR, module_path)

    if not os.path.isfile(full_path):
        messagebox.showerror("Module Not Found",
            f"Could not find the module file:\n\n{full_path}\n\n"
            f"Please check that the file exists and that the 'path' in\n"
            f"config.json is correct.")
        return

    try:
        subprocess.Popen(
            [sys.executable, full_path],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except FileNotFoundError:
        messagebox.showerror("Python Not Found",
            f"Python could not be found on this system.\n\n"
            f"Please install Python 3.6+ and ensure it is in your PATH.\n\n"
            f"Download: https://python.org/downloads")
    except Exception as e:
        messagebox.showerror("Launch Error",
            f"Failed to launch the module:\n\n{full_path}\n\n"
            f"Error: {e}")


# ---------------------------------------------------------------------------
# CustomTkinter GUI
# ---------------------------------------------------------------------------

class ModuleCard(ctk.CTkFrame):
    """A modern card widget for each module."""

    def __init__(self, parent, module: dict, on_launch, **kwargs):
        super().__init__(parent, **kwargs)
        self.module = module
        self.on_launch = on_launch

        # Hover state tracking
        self._hovering = False
        self._border_color = THEME["card_border"]

        self._build()
        self._bind_events()

    def _build(self):
        # Main card layout
        self.configure(
            fg_color="transparent",
            border_width=1,
            border_color=self._border_color,
            corner_radius=12,
        )

        # Inner content frame
        self.inner = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            bg_color=THEME["card_bg"],
            corner_radius=12,
        )
        self.inner.pack(fill="x", expand=True, padx=0, pady=0)

        # Arrow icon + name
        icon_label = ctk.CTkLabel(
            self.inner,
            text="\u25B6",
            font=("Segoe UI", 14, "bold"),
            text_color=THEME["icon_fg"],
            width=24,
        )
        icon_label.pack(side="left", padx=(16, 8), pady=14)

        name_label = ctk.CTkLabel(
            self.inner,
            text=self.module["name"],
            font=("Segoe UI", 14, "bold"),
            text_color=THEME["title_fg"],
            anchor="w",
        )
        name_label.pack(side="left", fill="x", expand=True, pady=14)

        # Launch button
        self.launch_btn = ctk.CTkButton(
            self.inner,
            text="Launch",
            font=("Segoe UI", 12, "bold"),
            fg_color=THEME["btn_bg"],
            hover_color=THEME["btn_hover"],
            text_color=THEME["btn_fg"],
            corner_radius=8,
            width=80,
            height=32,
            command=self.on_launch,
        )
        self.launch_btn.pack(side="right", padx=(0, 16), pady=10)

    def _bind_events(self):
        def on_enter(event=None):
            self._hovering = True
            self.configure(border_color=THEME["card_border_hover"])
            self.inner.configure(fg_color=THEME["card_hover"])
            self.launch_btn.configure(fg_color=THEME["btn_hover"])

        def on_leave(event=None):
            self._hovering = False
            self.configure(border_color=THEME["card_border"])
            self.inner.configure(fg_color=THEME["card_bg"])
            self.launch_btn.configure(fg_color=THEME["btn_bg"])

        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)
        self.inner.bind("<Enter>", on_enter)
        self.inner.bind("<Leave>", on_leave)


class LauncherApp(ctk.CTk):
    """Main launcher application window."""

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("560x600")
        self.minsize(420, 450)

        # Dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Load config
        self.config = load_config()
        self.app_name = self.config.get("app_name", APP_NAME)
        self.modules = self.config.get("modules", [])

        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.configure(fg_color=THEME["bg"])

        # Set icon if available
        icon_path = os.path.join(SCRIPT_DIR, "assets", "icon.png")
        if os.path.isfile(icon_path):
            try:
                self.iconbitmap(os.path.abspath(icon_path))
            except Exception:
                pass

    def _build_ui(self):
        # ---- Top accent bar (thin colored strip) ----
        accent_bar = ctk.CTkFrame(self, fg_color=THEME["accent"], height=3)
        accent_bar.pack(fill="x", side="top")
        accent_bar.pack_propagate(False)

        # ---- Top padding ----
        ctk.CTkFrame(self, height=24).pack(fill="x")

        # ---- Title ----
        title = ctk.CTkLabel(
            self,
            text=self.app_name,
            font=("Segoe UI", 26, "bold"),
            text_color=THEME["title_fg"],
        )
        title.pack(pady=(0, 6))

        # ---- Subtitle ----
        subtitle = ctk.CTkLabel(
            self,
            text="Choose a module to get started",
            font=("Segoe UI", 12),
            text_color=THEME["subtitle_fg"],
        )
        subtitle.pack(pady=(0, 24))

        # ---- Module cards (scrollable) ----
        if not self.modules:
            self._build_empty_state()
        else:
            self._build_module_cards()

        # ---- Bottom padding ----
        ctk.CTkFrame(self, height=16).pack(fill="x")

        # ---- Footer ----
        footer = ctk.CTkLabel(
            self,
            text=APP_FOOTER,
            font=("Segoe UI", 9),
            text_color=THEME["footer_fg"],
        )
        footer.pack(pady=(0, 16))

    def _build_empty_state(self):
        card = ctk.CTkFrame(
            self,
            fg_color=THEME["card_bg"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["card_border"],
        )
        card.pack(fill="x", padx=30, expand=True)
        card.configure(width=500)
        card.update()

        msg = ctk.CTkLabel(
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
            text_color=THEME["error_fg"],
            wraplength=440,
            justify="center",
        )
        msg.pack(pady=30, padx=20)

    def _build_module_cards(self):
        # Scrollable container
        scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=THEME["bg"],
            border_color=THEME["bg"],
        )
        scroll_frame.pack(fill="both", expand=True, padx=30)

        for i, module in enumerate(self.modules):
            card = ModuleCard(
                scroll_frame,
                module=module,
                on_launch=lambda p=module["path"]: self._on_launch(p),
                fg_color=THEME["bg"],
                border_width=1,
                border_color=THEME["card_border"],
                corner_radius=12,
            )
            card.pack(fill="x", pady=(4, 0))

    def _on_launch(self, module_path: str):
        """Handle the Launch button click."""
        launch_module(module_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Create and run the launcher application."""
    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Launcher closed.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERR] Launcher failed to start: {e}")
        sys.exit(1)
