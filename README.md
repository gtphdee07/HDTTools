# HDTTools

Tools for extracting structured data from heavy-duty-truck paperwork —
CAT Scale weigh tickets and vehicle Safety Compliance Certification labels
(truck and trailer) — via photo. Each reader prompts the user to pick an
image, extracts the printed fields, shows an editable review form so the
user can correct any misreads, then saves the result to a local SQLite
database.

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for Python and
dependency management.

```
uv sync
```

### API key (for the Claude-vision readers)

`read_scale_ticket`, `read_truck_tag`, and `read_trailer_tag` extract data
via the Claude API and require an `ANTHROPIC_API_KEY` environment variable.

### Tesseract (for the no-API-key OCR alternative)

`hdttools.scale_ticket_ocr.read_scale_ticket` is a drop-in alternative to
the scale ticket reader that uses local OCR instead of the Claude API, so
no API key or network access is needed. It requires the Tesseract OCR
engine installed separately (not just the `pytesseract` pip package). On
Windows: install from the community builds at
https://github.com/UB-Mannheim/tesseract/wiki. It's auto-detected on PATH
or at the default install location (`C:\Program Files\Tesseract-OCR`).

Accuracy is noticeably lower than the Claude-vision version, particularly
for fields near dense boilerplate text or small print — that's what the
review/repair step is for.

## Usage

```python
from hdttools import read_scale_ticket, read_truck_tag, read_trailer_tag

ticket = read_scale_ticket()   # prompts for a file, review/repair, then saves
truck = read_truck_tag()       # prompts for a file + vehicle name, review/repair, then saves
trailer = read_trailer_tag()   # prompts for a file + vehicle name, review/repair, then saves
```

Each function returns the saved record, or `None` if the user cancels the
review step instead of saving. Records are saved to `hdttools.db`
(SQLite) in the working directory, one table per record type
(`scale_tickets`, `truck_tags`, `trailer_tags`).

## Testing

```
uv run pytest -q
```

Or with coverage:

```
uv run pytest --cov
```

## Project layout

- `src/hdttools/models.py` — dataclasses for extracted records
- `src/hdttools/vision_client.py` — shared Claude-vision extraction helper
- `src/hdttools/file_picker.py` — shared file-picker / vehicle-name prompt (no API dependency)
- `src/hdttools/scale_ticket.py`, `truck_tag.py`, `trailer_tag.py` — Claude-vision readers
- `src/hdttools/scale_ticket_ocr.py` — local-OCR alternative for scale tickets
- `src/hdttools/review_form.py` — generic GUI review/repair form
- `src/hdttools/database.py` — SQLite persistence
- `tests/` — pytest suite
