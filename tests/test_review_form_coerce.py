import pytest

from hdttools.review_form import _coerce


@pytest.mark.parametrize(
    "raw, type_hint, expected",
    [
        ("Goose", str, "Goose"),
        ("", str, ""),
        ("34,400", float | None, 34400.0),
        ("34400", float, 34400.0),
        ("", float | None, None),
        ("true", bool, True),
        ("YES", bool, True),
        ("no", bool, False),
        ("", bool, False),
    ],
)
def test_coerce_valid_inputs(raw, type_hint, expected):
    assert _coerce(raw, type_hint) == expected


def test_coerce_invalid_float_raises_value_error():
    with pytest.raises(ValueError):
        _coerce("not-a-number", float | None)
