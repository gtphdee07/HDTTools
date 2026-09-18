"""Real-process regression test for a production bug (found 2026-09-18):
Streamlit Community Cloud installed dependencies from
`streamlit_app/requirements.txt` (its own, separately maintained list -
`streamlit`, `pillow`, `pytesseract` only), not `pyproject.toml`, so
`anthropic` was never installed there. `vision_client.py` imported it
unconditionally at module level, so importing `hdttools.scale_ticket`/
`trailer_tag`/`truck_tag` for their headless `extract_*_fields`
functions crashed the whole app at import time - even though the
deployed app runs `HDTTOOLS_OCR_BACKEND=tesseract` (the default) and
never actually calls `extract_via_claude`.

Same shape of bug, and same fix, as the tkinter-import crash fixed
earlier this session (`tests/test_optional_tkinter_import.py`,
`858d829`) - runs in a real subprocess with
`sys.modules["anthropic"] = None` (forces any `import anthropic` to
raise ImportError, simulating it genuinely not being installed) rather
than monkeypatching this process's own already-imported modules.
"""

from __future__ import annotations

import subprocess
import sys

_SCRIPT = """
import sys
sys.modules["anthropic"] = None

from hdttools import scale_ticket, trailer_tag, truck_tag, vision_client
print("IMPORT_OK")

try:
    vision_client.extract_via_claude(
        image_bytes=b"fake",
        media_type="image/jpeg",
        system_prompt="system",
        tool_name="record_scale_ticket",
        tool_description="desc",
        schema={"type": "object", "properties": {}},
    )
except RuntimeError as exc:
    print(f"EXTRACT_VIA_CLAUDE_ERROR:{exc}")
"""


def test_reader_modules_import_and_fail_loud_without_anthropic():
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout
    assert "EXTRACT_VIA_CLAUDE_ERROR:" in result.stdout
    assert "anthropic" in result.stdout.lower()
