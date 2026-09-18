"""Shared, dependency-light helpers for picking a file and naming a vehicle.

Kept separate from `vision_client` so extraction backends that don't use
the Claude API (e.g. local OCR) don't need to import anthropic at all.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    # tkinter isn't always present (e.g. Streamlit Community Cloud's
    # Python image lacks libtk8.6.so) - only select_image_file() actually
    # needs it, and only the desktop CLI readers call that, so importing
    # this module must still succeed for headless callers (the web API,
    # Streamlit) that never reach this function.
    tk = None
    filedialog = None

_IMAGE_FILETYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.webp"),
    ("All files", "*.*"),
]


def select_image_file(title: str) -> Path:
    """Open a native file-picker dialog and return the chosen image path."""
    if tk is None:
        raise RuntimeError(
            "tkinter is not available in this environment. select_image_file() "
            "requires a desktop display and can't run in a headless/server "
            "deployment (e.g. Streamlit Community Cloud) - use the headless "
            "extract_*_fields functions instead."
        )
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askopenfilename(title=title, filetypes=_IMAGE_FILETYPES)
    finally:
        root.destroy()

    if not selected:
        raise ValueError("No file was selected.")

    return Path(selected)


def prompt_vehicle_name() -> str:
    name = input("Enter a name for this vehicle: ").strip()
    if not name:
        raise ValueError("A vehicle name is required.")
    return name
