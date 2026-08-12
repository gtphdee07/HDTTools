import pytest

from hdttools import file_picker


class _FakeRoot:
    def __init__(self):
        self.destroyed = False

    def withdraw(self):
        pass

    def attributes(self, *args, **kwargs):
        pass

    def destroy(self):
        self.destroyed = True


def test_select_image_file_returns_chosen_path(monkeypatch, tmp_path):
    fake_root = _FakeRoot()
    monkeypatch.setattr(file_picker.tk, "Tk", lambda: fake_root)
    chosen = str(tmp_path / "ticket.jpg")
    monkeypatch.setattr(file_picker.filedialog, "askopenfilename", lambda **kwargs: chosen)

    result = file_picker.select_image_file("Select a file")

    assert str(result) == chosen
    assert fake_root.destroyed is True


def test_select_image_file_raises_when_dialog_cancelled(monkeypatch):
    fake_root = _FakeRoot()
    monkeypatch.setattr(file_picker.tk, "Tk", lambda: fake_root)
    monkeypatch.setattr(file_picker.filedialog, "askopenfilename", lambda **kwargs: "")

    with pytest.raises(ValueError):
        file_picker.select_image_file("Select a file")

    assert fake_root.destroyed is True


def test_prompt_vehicle_name_strips_whitespace(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "  Goose  ")
    assert file_picker.prompt_vehicle_name() == "Goose"


def test_prompt_vehicle_name_raises_on_blank_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "   ")
    with pytest.raises(ValueError):
        file_picker.prompt_vehicle_name()
