"""Generic GUI review/repair step: shows a form pre-filled with an
extracted record's fields (including nested dataclasses like TireSpec),
lets the user correct any of them, and returns the edited record."""

from __future__ import annotations

import dataclasses
import tkinter as tk
import typing
from tkinter import ttk
from typing import Any


def _leaf_fields(instance: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Walks `instance`'s dataclass fields (descending into nested
    dataclasses) and returns `(path, type_hint)` for every leaf field, in
    declaration order. Pure - no widgets, no Tkinter - so this is directly
    testable without a real window (tests/test_review_form_rebuild.py)."""
    hints = typing.get_type_hints(type(instance))
    fields: list[tuple[tuple[str, ...], Any]] = []
    for f in dataclasses.fields(instance):
        value = getattr(instance, f.name)
        path = prefix + (f.name,)
        if dataclasses.is_dataclass(value):
            fields.extend(_leaf_fields(value, path))
        else:
            fields.append((path, hints.get(f.name, str)))
    return fields


def _rebuild_from_values(instance: Any, values: dict[tuple[str, ...], str], prefix: tuple[str, ...] = ()) -> Any:
    """Reconstructs `instance` with every leaf field replaced by
    `_coerce(values[path], type_hint)`. Mirrors `_leaf_fields`'s own
    walk/path shape exactly, so the two are meant to be used together
    (see the round-trip test). Pure - the widget layer's job is only to
    turn live Entry widgets into this flat `values` dict first."""
    hints = typing.get_type_hints(type(instance))
    updates: dict[str, Any] = {}
    for f in dataclasses.fields(instance):
        value = getattr(instance, f.name)
        path = prefix + (f.name,)
        if dataclasses.is_dataclass(value):
            updates[f.name] = _rebuild_from_values(value, values, path)
        else:
            updates[f.name] = _coerce(values[path], hints.get(f.name, str))
    return dataclasses.replace(instance, **updates)


def _resolve_path(instance: Any, prefix: tuple[str, ...]) -> Any:
    """Walks `prefix`'s nested-dataclass attribute names and returns the
    instance they point at (e.g. `prefix=("tire",)` returns `instance.tire`)."""
    for name in prefix:
        instance = getattr(instance, name)
    return instance


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

    entries: dict[tuple[str, ...], tk.StringVar] = {}
    result: dict[str, Any] = {"value": None}
    row = [0]
    seen_headings: set[tuple[str, ...]] = set()

    for path, _hint in _leaf_fields(record):
        prefix = path[:-1]
        for depth in range(1, len(prefix) + 1):
            heading_path = prefix[:depth]
            if heading_path in seen_headings:
                continue
            seen_headings.add(heading_path)
            heading = " > ".join(heading_path).replace("_", " ").title()
            ttk.Label(
                container, text=heading, font=("Segoe UI", 9, "bold")
            ).grid(row=row[0], column=0, columnspan=2, sticky="w", pady=(10, 2))
            row[0] += 1

        label_text = " > ".join(path).replace("_", " ").title()
        ttk.Label(container, text=label_text).grid(
            row=row[0], column=0, sticky="w", padx=(12 * len(prefix), 6), pady=2
        )
        current = getattr(_resolve_path(record, prefix), path[-1])
        var = tk.StringVar(value="" if current is None else str(current))
        ttk.Entry(container, textvariable=var, width=42).grid(
            row=row[0], column=1, sticky="ew", pady=2
        )
        entries[path] = var
        row[0] += 1

    error_var = tk.StringVar()
    ttk.Label(container, textvariable=error_var, foreground="red").grid(
        row=row[0], column=0, columnspan=2, sticky="w", pady=(6, 0)
    )
    row[0] += 1

    def on_save() -> None:
        values = {path: var.get() for path, var in entries.items()}
        try:
            result["value"] = _rebuild_from_values(record, values)
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
