"""Explicit opt-in summary delivery; destinations come from environment variables."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def notify(channel: str, message: str) -> None:
    if channel == "slack":
        url = os.environ.get("FINOPS_SLACK_WEBHOOK", "")
        if not url.startswith("https://hooks.slack.com/services/"):
            raise ValueError("Set FINOPS_SLACK_WEBHOOK to an HTTPS Slack incoming webhook")
        payload = {"text": message[:3000]}
    else:
        token = os.environ.get("FINOPS_TELEGRAM_TOKEN", "")
        chat = os.environ.get("FINOPS_TELEGRAM_CHAT_ID", "")
        if not token or not chat or any(c in token for c in "/?#"):
            raise ValueError("Set FINOPS_TELEGRAM_TOKEN and FINOPS_TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat, "text": message[:3000]}
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError("Notification delivery failed")
    except (HTTPError, URLError, TimeoutError):
        # URLs can contain secrets; do not include the exception or destination.
        raise RuntimeError(
            "Notification delivery failed; check destination and connectivity"
        ) from None
