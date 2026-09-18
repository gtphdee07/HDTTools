"""Real-process regression test for a production bug (found 2026-09-18):
Streamlit Community Cloud's Python image doesn't ship tkinter's system
library (`libtk8.6.so`), so importing `hdttools.scale_ticket`/
`trailer_tag`/`truck_tag` there crashed the whole app at import time -
even though `streamlit_app/app.py` and `src/hdttools/api/main.py` never
call the tkinter-based `review_and_edit`/`select_image_file` functions,
only the headless `extract_*_fields` ones.

Runs in a real subprocess with `sys.modules["tkinter"] = None` (forces
any `import tkinter` to raise ImportError, simulating tkinter genuinely
not being installed) rather than monkeypatching this process's own
`sys.modules` - that would risk poisoning every other test's already-
imported `hdttools.file_picker`/`review_form` module objects.
"""

from __future__ import annotations

import subprocess
import sys

_SCRIPT = """
import sys
sys.modules["tkinter"] = None

from hdttools import file_picker, review_form, scale_ticket, trailer_tag, truck_tag
print("IMPORT_OK")

try:
    file_picker.select_image_file("Select a file")
except RuntimeError as exc:
    print(f"SELECT_IMAGE_FILE_ERROR:{exc}")

try:
    review_form.review_and_edit(object())
except RuntimeError as exc:
    print(f"REVIEW_AND_EDIT_ERROR:{exc}")
"""


def test_reader_modules_import_and_fail_loud_without_tkinter():
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "IMPORT_OK" in result.stdout
    assert "SELECT_IMAGE_FILE_ERROR:tkinter is not available" in result.stdout
    assert "REVIEW_AND_EDIT_ERROR:tkinter is not available" in result.stdout
