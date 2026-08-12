"""Generic GUI review/repair step: shows a form pre-filled with an
extracted record's fields (including nested dataclasses like TireSpec),
lets the user correct any of them, and returns the edited record."""

from __future__ import annotations

import dataclasses
import tkinter as tk
import typing
from tkinter import ttk
from typing import Any


def review_and_edit(record: Any) -> Any | None:
    """Show a form pre-filled with `record`'s fields. Returns the edited
    dataclass instance, or None if the user cancels."""
    cls = type(record)
    root = tk.Tk()
    root.title(f"Review {cls.__name__}")
    root.attributes("-topmost", True)

    container = ttk.Frame(root, padding=12)
    container.pack(fill="both", expand=True)
    container.columnconfigure(1, weight=1)

    entries: dict[tuple[str, ...], tuple[tk.StringVar, Any]] = {}
    result: dict[str, Any] = {"value": None}
    row = [0]

    def add_fields(instance: Any, prefix: tuple[str, ...] = ()) -> None:
        hints = typing.get_type_hints(type(instance))
        for f in dataclasses.fields(instance):
            value = getattr(instance, f.name)
            path = prefix + (f.name,)

            if dataclasses.is_dataclass(value):
                heading = " > ".join(path).replace("_", " ").title()
                ttk.Label(
                    container, text=heading, font=("Segoe UI", 9, "bold")
                ).grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(10, 2))
                row[0] += 1
                add_fields(value, path)
                continue

            label_text = " > ".join(path).replace("_", " ").title()
            ttk.Label(container, text=label_text).grid(
                row=row[0], column=0, sticky="w", padx=(12 * len(prefix), 6), pady=2
            )
            var = tk.StringVar(value="" if value is None else str(value))
            ttk.Entry(container, textvariable=var, width=42).grid(
                row=row[0], column=1, sticky="ew", pady=2
            )
            entries[path] = (var, hints.get(f.name, str))
            row[0] += 1

    add_fields(record)

    error_var = tk.StringVar()
    ttk.Label(container, textvariable=error_var, foreground="red").grid(
        row=row[0], column=0, columnspan=2, sticky="w", pady=(6, 0)
    )
    row[0] += 1

    def rebuild(instance: Any, prefix: tuple[str, ...] = ()) -> Any:
        updates = {}
        for f in dataclasses.fields(instance):
            value = getattr(instance, f.name)
            path = prefix + (f.name,)
            if dataclasses.is_dataclass(value):
                updates[f.name] = rebuild(value, path)
            else:
                var, hint = entries[path]
                updates[f.name] = _coerce(var.get(), hint)
        return dataclasses.replace(instance, **updates)

    def on_save() -> None:
        try:
            result["value"] = rebuild(record)
        except ValueError as exc:
            error_var.set(str(exc))
            return
        root.destroy()

    def on_cancel() -> None:
        result["value"] = None
        root.destroy()

    button_row = ttk.Frame(container)
    button_row.grid(row=row[0], column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(button_row, text="Cancel", command=on_cancel).pack(side="right", padx=(6, 0))
    ttk.Button(button_row, text="Save", command=on_save).pack(side="right")

    root.mainloop()
    return result["value"]


def _coerce(raw: str, type_hint: Any) -> Any:
    raw = raw.strip()
    args = typing.get_args(type_hint)
    optional = type(None) in args
    real_type = next((a for a in args if a is not type(None)), type_hint)

    if raw == "":
        if optional:
            return None
        if real_type is bool:
            return False
        return ""

    if real_type is bool:
        return raw.lower() in ("1", "true", "yes", "y")
    if real_type is float:
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            raise ValueError(f"'{raw}' is not a valid number.") from None

    return raw
