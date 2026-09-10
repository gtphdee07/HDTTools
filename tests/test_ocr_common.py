"""Function tests for `ocr_common.get_ocr_backend` - the single build/
env-level flag (`HDTTOOLS_OCR_BACKEND`) both `src/hdttools/api/main.py`
and `streamlit_app/app.py` read to choose Tesseract-style vs
Claude-vision-style extraction (roadmap item #16). Default is
"tesseract" so no existing deployment starts requiring
`ANTHROPIC_API_KEY` without opting in; an invalid value raises loudly
rather than silently falling back to a default."""

import pytest

from hdttools.ocr_common import get_ocr_backend


def test_get_ocr_backend_defaults_to_tesseract_when_unset(monkeypatch):
    monkeypatch.delenv("HDTTOOLS_OCR_BACKEND", raising=False)
    assert get_ocr_backend() == "tesseract"


def test_get_ocr_backend_reads_explicit_tesseract_value(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "tesseract")
    assert get_ocr_backend() == "tesseract"


def test_get_ocr_backend_reads_explicit_claude_value(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "claude")
    assert get_ocr_backend() == "claude"


def test_get_ocr_backend_raises_on_invalid_value(monkeypatch):
    monkeypatch.setenv("HDTTOOLS_OCR_BACKEND", "bogus")
    with pytest.raises(ValueError, match="bogus"):
        get_ocr_backend()
