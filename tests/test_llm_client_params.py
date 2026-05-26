from app.config import settings
from app.core.llm_client import LLMClient


class _FakeMessage:
    content = "ok"


class _FakeChoice:
    message = _FakeMessage()


class _FakeResponse:
    choices = [_FakeChoice()]


class _FakeCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _FakeResponse()


class _FakeOpenAIClient:
    def __init__(self):
        self.completions = _FakeCompletions()
        self.chat = type("Chat", (), {"completions": self.completions})()


def _client_with_fake_openai():
    client = LLMClient.__new__(LLMClient)
    client.openai_client = _FakeOpenAIClient()
    client.call_count = 0
    return client


def test_gpt5_chat_completion_uses_supported_params(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_TEXT_MODEL", "gpt-5-nano")
    client = _client_with_fake_openai()

    client.generate_text("system", "user", temperature=0.3)

    kwargs = client.openai_client.completions.kwargs
    assert kwargs["model"] == "gpt-5-nano"
    assert kwargs["max_completion_tokens"] == 16000
    assert "max_tokens" not in kwargs
    assert "temperature" not in kwargs


def test_legacy_chat_completion_keeps_existing_params(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_TEXT_MODEL", "gpt-4o-mini")
    client = _client_with_fake_openai()

    client.generate_text("system", "user", temperature=0.3)

    kwargs = client.openai_client.completions.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["max_tokens"] == 16000
    assert kwargs["temperature"] == 0.3
    assert "max_completion_tokens" not in kwargs
