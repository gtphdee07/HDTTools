import pytest

from hdttools import vision_client


class _FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, name, input_data):
        self.name = name
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, response):
        self._response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class _FakeAnthropicClient:
    def __init__(self, response):
        self.messages = _FakeMessages(response)


def test_extract_via_claude_returns_tool_input(tmp_path, monkeypatch):
    image_path = tmp_path / "ticket.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    fake_response = _FakeResponse(
        [_FakeToolUseBlock("record_scale_ticket", {"ticket_number": "123"})]
    )
    fake_client = _FakeAnthropicClient(fake_response)
    monkeypatch.setattr(vision_client.anthropic, "Anthropic", lambda: fake_client)

    result = vision_client.extract_via_claude(
        image_path=image_path,
        system_prompt="system",
        tool_name="record_scale_ticket",
        tool_description="desc",
        schema={"type": "object", "properties": {}},
    )

    assert result == {"ticket_number": "123"}
    assert fake_client.messages.last_kwargs["tool_choice"] == {
        "type": "tool",
        "name": "record_scale_ticket",
    }


def test_extract_via_claude_raises_without_tool_use_block(tmp_path, monkeypatch):
    image_path = tmp_path / "ticket.jpg"
    image_path.write_bytes(b"fake-image-bytes")

    fake_client = _FakeAnthropicClient(_FakeResponse([]))
    monkeypatch.setattr(vision_client.anthropic, "Anthropic", lambda: fake_client)

    with pytest.raises(RuntimeError):
        vision_client.extract_via_claude(
            image_path=image_path,
            system_prompt="system",
            tool_name="record_scale_ticket",
            tool_description="desc",
            schema={"type": "object", "properties": {}},
        )
