from experiments.BoundOCR.common.confidence import gate_fields


def test_gate_fields_blanks_a_field_that_fails_its_format_check():
    fields = {"gvwr_lb": -50.0, "manufacturer": "Ford Motor Co"}

    gated = gate_fields(fields, overall_confidence=95.0)

    assert gated["gvwr_lb"] is None
    assert gated["manufacturer"] == "Ford Motor Co"


def test_gate_fields_blanks_everything_below_the_confidence_threshold():
    fields = {
        "gvwr_lb": 7100.0,
        "front_gawr_lb": 3525.0,
        "manufacturer": "Ford Motor Co",
    }

    gated = gate_fields(fields, overall_confidence=10.0)

    assert gated == {
        "gvwr_lb": None,
        "front_gawr_lb": None,
        "manufacturer": None,
    }
