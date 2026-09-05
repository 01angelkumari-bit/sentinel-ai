from base64 import urlsafe_b64decode
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application.auth.email_service import EmailDeliveryError, SmtpEmailService


@pytest.fixture(autouse=True)
def clear_gmail_token_cache():
    from app.application.auth.email_service import _gmail_token_cache
    _gmail_token_cache.update(key="", token="", expires_at=0.0)


class Response:
    def __init__(self, payload: dict | None = None, failure: Exception | None = None) -> None:
        self.payload = payload or {}
        self.failure = failure

    def raise_for_status(self) -> None:
        if self.failure:
            raise self.failure

    def json(self) -> dict:
        return self.payload


def gmail_settings() -> SimpleNamespace:
    return SimpleNamespace(
        email_provider="gmail_api",
        email_from="01sentinelai@gmail.com",
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_refresh_token="refresh-token",
        otp_expire_minutes=10,
        email_delivery_timeout_seconds=8,
    )


def test_gmail_api_sends_encoded_otp_message(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    def post(url: str, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/token"):
            return Response({"access_token": "access-token", "expires_in": 3600})
        return Response({"id": "message-id"})

    monkeypatch.setattr("app.application.auth.email_service.requests.post", post)
    service = SmtpEmailService()
    service.settings = gmail_settings()
    service.send_otp("recipient@gmail.com", "A7K29P", "registration")

    assert calls[0][1]["data"]["refresh_token"] == "refresh-token"
    assert calls[1][1]["headers"] == {"Authorization": "Bearer access-token"}
    encoded = calls[1][1]["json"]["raw"]
    decoded = urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode()
    assert "To: recipient@gmail.com" in decoded
    assert "A7K29P" in decoded


def test_gmail_api_reuses_access_token_for_fast_resends(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def post(url: str, **kwargs):
        calls.append(url)
        if url.endswith("/token"):
            return Response({"access_token": "access-token", "expires_in": 3600})
        return Response({"id": "message-id"})

    monkeypatch.setattr("app.application.auth.email_service.requests.post", post)
    service = SmtpEmailService()
    service.settings = gmail_settings()
    service.send_otp("recipient@gmail.com", "A7K29P", "registration")
    service.send_otp("recipient@gmail.com", "B8L30Q", "registration")

    assert sum(url.endswith("/token") for url in calls) == 1
    assert sum("messages/send" in url for url in calls) == 2


def test_gmail_api_failure_is_converted_to_delivery_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    monkeypatch.setattr(
        "app.application.auth.email_service.requests.post",
        lambda *args, **kwargs: Response(failure=requests.HTTPError("unauthorized")),
    )
    service = SmtpEmailService()
    service.settings = gmail_settings()

    with pytest.raises(EmailDeliveryError):
        service.send_otp("recipient@gmail.com", "A7K29P", "login")
