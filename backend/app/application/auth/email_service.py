from __future__ import annotations

import smtplib
import ssl
import base64
import hashlib
from email.message import EmailMessage
from threading import Lock
from time import monotonic

import dns.exception
import dns.resolver
import requests

from app.core.config import get_settings


class EmailConfigurationError(RuntimeError): pass
class EmailDeliveryError(RuntimeError): pass
class EmailDomainError(ValueError): pass


_gmail_token_lock = Lock()
_gmail_token_cache: dict[str, str | float] = {"key": "", "token": "", "expires_at": 0.0}


def validate_mx_domain(email: str) -> None:
    domain = email.rsplit("@", 1)[-1].lower().rstrip(".")
    if not domain or domain in {"example.com", "example.org", "example.net", "localhost", "test"}:
        raise EmailDomainError("Use an email address with a deliverable mail domain")
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        if not list(answers): raise EmailDomainError("The email domain does not accept mail")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        raise EmailDomainError("The email domain does not have a reachable mail server") from exc


class SmtpEmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _configured(self) -> None:
        if not self.settings.email_from:
            raise EmailConfigurationError("Email delivery is not configured")
        if self.settings.email_provider == "gmail_api":
            if not all((self.settings.google_client_id, self.settings.google_client_secret, self.settings.google_refresh_token)):
                raise EmailConfigurationError("Gmail API delivery is not configured")
        elif not self.settings.smtp_host:
            raise EmailConfigurationError("SMTP delivery is not configured")

    def ensure_configured(self) -> None:
        self._configured()

    def _gmail_access_token(self) -> str:
        cache_key = hashlib.sha256(
            f"{self.settings.google_client_id}:{self.settings.google_refresh_token}".encode()
        ).hexdigest()
        with _gmail_token_lock:
            if (
                _gmail_token_cache["key"] == cache_key
                and _gmail_token_cache["token"]
                and monotonic() < float(_gmail_token_cache["expires_at"])
            ):
                return str(_gmail_token_cache["token"])
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": self.settings.google_refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=self.settings.email_delivery_timeout_seconds,
            )
            token_response.raise_for_status()
            payload = token_response.json()
            access_token = str(payload["access_token"])
            expires_in = max(120, int(payload.get("expires_in", 3600)))
            _gmail_token_cache.update(
                key=cache_key,
                token=access_token,
                expires_at=monotonic() + expires_in - 60,
            )
            return access_token

    def _send_gmail_api(self, message: EmailMessage) -> None:
        try:
            access_token = self._gmail_access_token()
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
            send_response = requests.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw_message},
                timeout=self.settings.email_delivery_timeout_seconds,
            )
            send_response.raise_for_status()
        except (KeyError, ValueError, requests.RequestException) as exc:
            raise EmailDeliveryError("Verification email delivery failed") from exc

    def send_otp(self, recipient: str, code: str, purpose: str) -> None:
        self._configured()
        label = {"registration": "verify your Sentinel AI account", "login": "sign in to Sentinel AI", "password_reset": "reset your Sentinel AI password"}[purpose]
        message = EmailMessage()
        message["Subject"] = f"Sentinel AI verification code: {code}"
        message["From"] = self.settings.email_from
        message["To"] = recipient
        message.set_content(f"Use this one-time code to {label}:\n\n{code}\n\nThis code expires in {self.settings.otp_expire_minutes} minutes. If you did not request it, ignore this email. Never share this code.")
        if self.settings.email_provider == "gmail_api":
            self._send_gmail_api(message)
            return
        try:
            context = ssl.create_default_context()
            timeout = self.settings.email_delivery_timeout_seconds
            client_connection = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=timeout, context=context) if self.settings.smtp_use_ssl else smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=timeout)
            with client_connection as client:
                if not self.settings.smtp_use_ssl:
                    client.ehlo()
                    if self.settings.smtp_use_tls: client.starttls(context=context); client.ehlo()
                if self.settings.smtp_username: client.login(self.settings.smtp_username, self.settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Verification email delivery failed") from exc
