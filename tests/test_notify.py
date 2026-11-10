import json

import pytest

from finops_auditor.notify import notify


def test_slack_webhook_delivery(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResponse()

    monkeypatch.setenv("FINOPS_SLACK_WEBHOOK", "https://hooks.slack.com/services/T00/B00/X00")
    monkeypatch.setattr("finops_auditor.notify.urlopen", fake_urlopen)
    notify("slack", "hello")
    assert captured["url"] == "https://hooks.slack.com/services/T00/B00/X00"
    assert captured["body"] == {"text": "hello"}


def test_invalid_slack_webhook_url(monkeypatch):
    monkeypatch.setenv("FINOPS_SLACK_WEBHOOK", "http://insecure.example.com")
    with pytest.raises(ValueError, match="HTTPS Slack incoming webhook"):
        notify("slack", "hello")


def test_telegram_delivery(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=10):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResponse()

    monkeypatch.setenv("FINOPS_TELEGRAM_TOKEN", "123456:ABC-DEF")
    monkeypatch.setenv("FINOPS_TELEGRAM_CHAT_ID", "-100123456")
    monkeypatch.setattr("finops_auditor.notify.urlopen", fake_urlopen)
    notify("telegram", "alert")
    assert captured["url"] == "https://api.telegram.org/bot123456:ABC-DEF/sendMessage"
    assert captured["body"] == {"chat_id": "-100123456", "text": "alert"}


def test_telegram_invalid_token(monkeypatch):
    monkeypatch.setenv("FINOPS_TELEGRAM_TOKEN", "123456/invalid")
    monkeypatch.setenv("FINOPS_TELEGRAM_CHAT_ID", "123")
    with pytest.raises(ValueError):
        notify("telegram", "alert")


def test_network_failure_does_not_leak_secrets(monkeypatch):
    def fake_urlopen(req, timeout=10):
        from urllib.error import URLError

        raise URLError("connection refused")

    monkeypatch.setenv(
        "FINOPS_SLACK_WEBHOOK", "https://hooks.slack.com/services/T00/B00/SECRET_KEY"
    )
    monkeypatch.setattr("finops_auditor.notify.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError) as excinfo:
        notify("slack", "alert")
    assert "SECRET_KEY" not in str(excinfo.value)
