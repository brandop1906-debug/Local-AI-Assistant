"""
quote_generator.py
==================
A local, offline service quote generator powered by LM Studio.

This script:
  1. Collects service details via a rich GUI (categories, customer info, pricing)
  2. Loads a base quote template from /templates
  3. Combines the template with your description
  4. Sends the combined prompt to LM Studio's local server
  5. Displays the polished, formatted service quote
  6. Saves the quote to /output (TXT or PDF) with a timestamped filename

No cloud APIs required. Everything runs on your machine.

Requirements:
  - Python 3.6+
  - LM Studio installed and running: https://lmstudio.ai
  - A model loaded in LM Studio with the Local Server started
  - fpdf2 (pip install fpdf2) — for PDF export

Usage:
  python quote_generator.py
  (or double-click run.bat on Windows)
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from datetime import datetime
from io import BytesIO

# ---------------------------------------------------------------------------
# Force UTF-8 encoding on Windows so characters display correctly
# ---------------------------------------------------------------------------
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from utils.logging_config import get_logger

logger = get_logger("quote_generator")

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
            logger.warning("Failed to load %s: %s — using defaults", CONFIG_PATH, e)

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


def save_quote(content: str, fmt: str = "txt") -> str:
    """
    Save the quote content to /output with a timestamped filename.

    Args:
        content: The quote text to save.
        fmt:     Output format — 'txt' or 'pdf'.

    Returns:
        The full path to the saved file.
    """
    ensure_dir(OUTPUT_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "pdf":
        try:
            from fpdf import FPDF
        except ImportError:
            raise RuntimeError(
                "fpdf2 is required for PDF export.\n"
                "Install it with: pip install fpdf2"
            )
        filepath = os.path.join(OUTPUT_DIR, f"quote_{timestamp}.pdf")
        _save_as_pdf(content, filepath)
    else:
        filepath = os.path.join(OUTPUT_DIR, f"quote_{timestamp}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return filepath


def _save_as_pdf(content: str, filepath: str) -> None:
    """Render text content to a PDF using fpdf2."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Service Quote", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)

    # Separator
    pdf.set_draw_color(0, 102, 153)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Body text (split by newlines, apply basic formatting)
    pdf.set_font("Helvetica", "", 10.5)
    lines = content.splitlines()
    for line in lines:
        # Detect bold-like markers
        if line.startswith("**") and line.endswith("**"):
            pdf.set_font("Helvetica", "B", 10.5)
            line = line.strip("*")
        elif line.startswith("**"):
            pdf.set_font("Helvetica", "B", 10.5)
            # Find where bold ends
            end = line.find("**")
            if end > 0:
                pdf.cell(0, 5.5, line[:end], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", "", 10.5)
                pdf.cell(0, 5.5, line[end + 2:], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                continue
        else:
            pdf.set_font("Helvetica", "", 10.5)

        # Skip blank lines but add spacing
        if not line.strip():
            pdf.ln(3)
            continue

        # Use multi_cell for wrapping long lines
        pdf.multi_cell(0, 5.5, line)
        pdf.ln(0.5)

    # Footer
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Powered by LM Studio",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.output(filepath)


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
# Pricing Calculator (inline table)
# ---------------------------------------------------------------------------


class PricingCalculator(ttk.Frame):
    """Inline pricing table with add/remove rows and auto-totals."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)

        # Column headers
        headers = ["#", "Description", "Qty", "Unit Price ($)", "Total ($)", ""]
        col_widths = [25, 160, 40, 80, 80, 25]

        for i, (hdr, w) in enumerate(zip(headers, col_widths)):
            lbl = ttk.Label(self, text=hdr, font=("Segoe UI", 9, "bold"))
            lbl.grid(row=0, column=i, padx=(2 if i else 0), pady=3, sticky="ew")

        # Configure column weights for resizing
        self.columnconfigure(1, weight=1)

        # List to track row widgets
        self._rows: list[dict] = []
        # Row counter
        self._row_count = 0

        # Totals frame
        self._totals_frame = ttk.Frame(self)
        self._totals_frame.grid(row=1, column=0, columnspan=6, pady=(5, 2), sticky="ew")

        self.subtotal_var = tk.StringVar(value="Subtotal: $0.00")
        self.tax_var = tk.StringVar(value="Tax (10%): $0.00")
        self.total_var = tk.StringVar(value="Total: $0.00")

        ttk.Label(self._totals_frame, textvariable=self.subtotal_var,
                  font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 20), sticky="e")
        ttk.Label(self._totals_frame, textvariable=self.tax_var,
                  font=("Segoe UI", 9)).grid(row=0, column=1, padx=(0, 20), sticky="e")
        ttk.Label(self._totals_frame, textvariable=self.total_var,
                  font=("Segoe UI", 10, "bold"), foreground="#006699").grid(row=0, column=2, sticky="e")

        # Add row button
        self.add_btn = ttk.Button(self, text="+ Add Line Item", command=self._add_row)
        self.add_btn.grid(row=2, column=0, columnspan=6, pady=(3, 0))

    def _add_row(self) -> None:
        """Add a new pricing row."""
        self._row_count += 1
        row = self._row_count

        # Description
        desc_var = tk.StringVar()
        ttk.Entry(self, textvariable=desc_var, width=22).grid(row=row, column=1, padx=2, pady=2, sticky="ew")

        # Quantity
        qty_var = tk.StringVar(value="1")
        qty_spin = ttk.Spinbox(self, from_=1, to=999, textvariable=qty_var, width=5)
        qty_spin.grid(row=row, column=2, padx=2, pady=2)

        # Unit price
        price_var = tk.StringVar(value="0.00")
        ttk.Entry(self, textvariable=price_var, width=10).grid(row=row, column=3, padx=2, pady=2)

        # Total (read-only)
        total_var = tk.StringVar(value="$0.00")
        ttk.Label(self, textvariable=total_var, anchor="e", width=10, font=("Consolas", 9)).grid(
            row=row, column=4, padx=2, pady=2
        )

        # Remove button
        remove_btn = ttk.Button(self, text="✕", width=3,
                                command=lambda r=row: self._remove_row(r))
        remove_btn.grid(row=row, column=5, padx=2, pady=2)

        # Bind variable updates to recalculate
        qty_var.trace_add("write", lambda *_: self._recalculate())
        price_var.trace_add("write", lambda *_: self._recalculate())

        self._rows.append({"row": row, "desc": desc_var, "qty": qty_var, "price": price_var, "total": total_var})
        self._recalculate()

    def _remove_row(self, row: int) -> None:
        """Remove a pricing row."""
        info = next((r for r in self._rows if r["row"] == row), None)
        if not info:
            return
        # Clear grid
        for col in range(6):
            widgets = self.grid_slaves(row=row, column=col)
            for w in widgets:
                w.grid_forget()
                w.destroy()
        self._rows = [r for r in self._rows if r["row"] != row]
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate all row totals and the grand total."""
        subtotal = 0.0
        for info in self._rows:
            try:
                qty = float(info["qty"].get() or "0")
                price = float(info["price"].get() or "0")
            except ValueError:
                qty, price = 0, 0
            total = qty * price
            info["total"].set(f"${total:,.2f}")
            subtotal += total

        tax = subtotal * 0.10  # 10% default tax
        grand = subtotal + tax

        self.subtotal_var.set(f"Subtotal: ${subtotal:,.2f}")
        self.tax_var.set(f"Tax (10%): ${tax:,.2f}")
        self.total_var.set(f"Total: ${grand:,.2f}")

    def get_items(self) -> list[dict]:
        """Return a list of pricing items from all rows."""
        items = []
        for info in self._rows:
            desc = info["qty"].master.master.nametowidget(info["qty"].master.grid_info()["column"])
            # Simpler: just get the text directly
            entry_widgets = info["qty"].master.grid_slaves(column=1)
            desc_entry = entry_widgets[0] if entry_widgets else None
            desc_text = desc_entry.get() if desc_entry else ""
            try:
                qty = float(info["qty"].get() or "0")
                price = float(info["price"].get() or "0")
            except ValueError:
                continue
            if desc_text.strip():
                items.append({"description": desc_text, "qty": qty, "price": price, "total": qty * price})
        return items

    def get_items_simple(self) -> list[dict]:
        """Return a list of pricing items."""
        items = []
        for info in self._rows:
            desc_text = info["desc"].get()
            try:
                qty = float(info["qty"].get() or "0")
                price = float(info["price"].get() or "0")
            except ValueError:
                continue
            if desc_text.strip():
                items.append({"description": desc_text, "qty": qty, "price": price, "total": qty * price})
        return items


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------


class QuoteGeneratorGUI:
    """Tkinter-based GUI for the service quote generator."""

    SERVICE_CATEGORIES = [
        "Electrical Services",
        "Plumbing Services",
        "HVAC Services",
        "Carpentry / Woodworking",
        "Painting Services",
        "Landscaping / Lawn Care",
        "Cleaning Services",
        "Moving / Relocation",
        "IT / Computer Repair",
        "Auto Repair / Maintenance",
        "Roofing Services",
        "Drywall / Drywall Repair",
        "Window / Door Installation",
        "Appliance Repair",
        "General Handyman",
        "Other",
    ]

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Service Quote Generator (LM Studio)")
        self.root.geometry("850x750")
        self.root.minsize(600, 550)
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
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Title ----
        title_label = ttk.Label(
            main_frame,
            text="📋  Service Quote Generator",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=(0, 5))

        # ---- Subtitle / instructions ----
        subtitle = ttk.Label(
            main_frame,
            text="Fill in the details below, then click Generate to create a professional quote.",
            font=("Segoe UI", 9),
            foreground="gray",
        )
        subtitle.pack(pady=(0, 10))

        # ====================================================================
        # SECTION 1: Service Category Dropdown
        # ====================================================================
        cat_frame = ttk.LabelFrame(main_frame, text="Service Category", padding=10)
        cat_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(cat_frame, text="Category:").pack(side=tk.LEFT, padx=(0, 10))
        self.category_var = tk.StringVar(value=self.SERVICE_CATEGORIES[0])
        self.category_combo = ttk.Combobox(
            cat_frame,
            textvariable=self.category_var,
            values=self.SERVICE_CATEGORIES,
            state="readonly",
            width=40,
        )
        self.category_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ====================================================================
        # SECTION 2: Customer Information (optional)
        # ====================================================================
        cust_frame = ttk.LabelFrame(main_frame, text="Customer Information (optional)", padding=10)
        cust_frame.pack(fill=tk.X, pady=(0, 8))

        # Row 1: Name + Phone
        row1 = ttk.Frame(cust_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row1, text="Customer Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.customer_name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.customer_name_var, width=25).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Label(row1, text="Phone:").pack(side=tk.LEFT, padx=(0, 5))
        self.customer_phone_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.customer_phone_var, width=15).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Row 2: Address
        row2 = ttk.Frame(cust_frame)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="Address:").pack(side=tk.LEFT, padx=(0, 5))
        self.customer_address_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.customer_address_var, width=55).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ====================================================================
        # SECTION 3: Services Description
        # ====================================================================
        desc_frame = ttk.LabelFrame(main_frame, text="Services / Project Description", padding=10)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.desc_text = scrolledtext.ScrolledText(
            desc_frame,
            height=5,
            font=("Consolas", 10),
            wrap=tk.WORD,
        )
        self.desc_text.pack(fill=tk.BOTH, expand=True)
        self.desc_text.insert(
            tk.END,
            "e.g., Home office electrical wiring for a 12x10 room, "
            "including outlet installation, switch wiring, and ceiling light fixture. "
            "Client prefers daytime work and needs materials included.",
        )
        self.desc_text.bind("<FocusIn>", self._on_desc_focus_in)

        # ====================================================================
        # SECTION 4: Pricing Calculator
        # ====================================================================
        price_frame = ttk.LabelFrame(main_frame, text="Pricing Calculator (optional)", padding=10)
        price_frame.pack(fill=tk.X, pady=(0, 8))

        # Make the frame resizable by wrapping in a canvas for scrolling
        price_canvas = tk.Canvas(price_frame, highlightthickness=0)
        price_scroll = ttk.Scrollbar(price_frame, orient="vertical", command=price_canvas.yview)
        self.pricing_scrollable = ttk.Frame(price_canvas)
        self.pricing_scrollable.bind("<Configure>", lambda e: price_canvas.configure(scrollregion=price_canvas.bbox("all")))
        price_canvas.create_window((0, 0), window=self.pricing_scrollable, anchor="nw")
        price_canvas.configure(yscrollcommand=price_scroll.set)

        price_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        price_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Build the pricing calculator inside the scrollable frame
        self.pricing_calc = PricingCalculator(self.pricing_scrollable)
        self.pricing_calc.pack(fill=tk.BOTH, expand=True)

        # ====================================================================
        # SECTION 5: Generate button
        # ====================================================================
        self.generate_btn = ttk.Button(
            main_frame,
            text="⚡ Generate Quote",
            command=self._generate,
        )
        self.generate_btn.pack(pady=(5, 8))

        # ====================================================================
        # SECTION 6: Result area
        # ====================================================================
        result_frame = ttk.LabelFrame(main_frame, text="Generated Quote", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=10,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # ====================================================================
        # SECTION 7: Action buttons
        # ====================================================================
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)

        self.copy_btn = ttk.Button(
            action_frame,
            text="📋 Copy",
            command=self._copy_to_clipboard,
            state=tk.DISABLED,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.save_txt_btn = ttk.Button(
            action_frame,
            text="💾 Save TXT",
            command=lambda: self._save_quote("txt"),
            state=tk.DISABLED,
        )
        self.save_txt_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.save_pdf_btn = ttk.Button(
            action_frame,
            text="📄 Save PDF",
            command=lambda: self._save_quote("pdf"),
            state=tk.DISABLED,
        )
        self.save_pdf_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.open_btn = ttk.Button(
            action_frame,
            text="📂 Open Folder",
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
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

    def _on_desc_focus_in(self, event: tk.Event) -> None:
        """Clear placeholder text on focus."""
        placeholder = (
            "e.g., Home office electrical wiring for a 12x10 room, "
            "including outlet installation, switch wiring, and ceiling light fixture. "
            "Client prefers daytime work and needs materials included."
        )
        if self.desc_text.get(1.0, tk.END).strip() == placeholder:
            self.desc_text.delete(1.0, tk.END)

    def _build_prompt(self) -> str:
        """Build the full prompt from all GUI inputs."""
        category = self.category_var.get()
        customer_name = self.customer_name_var.get().strip()
        customer_phone = self.customer_phone_var.get().strip()
        customer_address = self.customer_address_var.get().strip()
        services_desc = self.desc_text.get(1.0, tk.END).strip()

        # Gather pricing items
        pricing_items = self.pricing_calc.get_items_simple()

        # Build customer info section
        customer_info_lines = []
        if customer_name:
            customer_info_lines.append(f"Customer Name: {customer_name}")
        if customer_phone:
            customer_info_lines.append(f"Phone: {customer_phone}")
        if customer_address:
            customer_info_lines.append(f"Address: {customer_address}")
        customer_block = "\n".join(customer_info_lines) if customer_info_lines else "Customer information will be filled in upon acceptance."

        # Build pricing section
        pricing_block = ""
        if pricing_items:
            pricing_lines = ["Pricing Breakdown:"]
            for i, item in enumerate(pricing_items, 1):
                pricing_lines.append(
                    f"  {i}. {item['description']}  |  Qty: {int(item['qty'])}  |  Unit: ${item['price']:,.2f}  |  Total: ${item['total']:,.2f}"
                )
            subtotal = sum(item["total"] for item in pricing_items)
            tax = subtotal * 0.10
            grand = subtotal + tax
            pricing_lines.append(f"\n  Subtotal: ${subtotal:,.2f}")
            pricing_lines.append(f"  Tax (10%):  ${tax:,.2f}")
            pricing_lines.append(f"  **Total: ${grand:,.2f}**")
            pricing_block = "\n".join(pricing_lines)

        # Load template
        template_text = load_template("quote_base")

        # Build prompt
        full_prompt = f"""{template_text}

=== INPUT DATA ===

Service Category: {category}

{customer_block}

Services / Project Description:
{services_desc}

{pricing_block}

==================

Please generate a complete, professional service quote based on the data above.
Include all standard sections: Header, Client Info, Scope of Work, Pricing, Terms, Contact.
Use the provided pricing data exactly as given. If the pricing section is empty, generate reasonable estimates.
Format the quote as a clean, ready-to-use document.
"""
        return full_prompt

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
            # Build prompt from all inputs
            full_prompt = self._build_prompt()

            # Call LM Studio
            quote_content = call_lm_studio(full_prompt)

            # Save to file (TXT by default)
            filepath = save_quote(quote_content, fmt="txt")

            # Display result
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, quote_content)
            self.result_text.config(state=tk.DISABLED)

            self.copy_btn.config(state=tk.NORMAL)
            self.save_txt_btn.config(state=tk.NORMAL)
            self.save_pdf_btn.config(state=tk.NORMAL)
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

    def _save_quote(self, fmt: str) -> None:
        """Save the current quote content to a file."""
        quote_content = self.result_text.get(1.0, tk.END).strip()
        if not quote_content:
            messagebox.showwarning("Nothing to save", "No quote has been generated yet.")
            return

        try:
            filepath = save_quote(quote_content, fmt=fmt)
            self.status_var.set(f"Saved as {fmt.upper()}: {filepath}")
            messagebox.showinfo("Saved", f"Quote saved as {fmt.upper()}!\n\n{filepath}")
        except RuntimeError as e:
            messagebox.showerror("Save Error", str(e))

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
