"""Shared, dependency-light helpers for picking a file and naming a vehicle.

Kept separate from `vision_client` so extraction backends that don't use
the Claude API (e.g. local OCR) don't need to import anthropic at all.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

_IMAGE_FILETYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.webp"),
    ("All files", "*.*"),
]


def select_image_file(title: str) -> Path:
    """Open a native file-picker dialog and return the chosen image path."""
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
