from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

import dns.exception
import dns.resolver

from app.core.config import get_settings


class EmailConfigurationError(RuntimeError): pass
class EmailDeliveryError(RuntimeError): pass
class EmailDomainError(ValueError): pass


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
        if not self.settings.smtp_host or not self.settings.email_from:
            raise EmailConfigurationError("Email delivery is not configured")

    def send_otp(self, recipient: str, code: str, purpose: str) -> None:
        self._configured()
        label = {"registration": "verify your Sentinel AI account", "login": "sign in to Sentinel AI", "password_reset": "reset your Sentinel AI password"}[purpose]
        message = EmailMessage()
        message["Subject"] = f"Sentinel AI verification code: {code}"
        message["From"] = self.settings.email_from
        message["To"] = recipient
        message.set_content(f"Use this one-time code to {label}:\n\n{code}\n\nThis code expires in {self.settings.otp_expire_minutes} minutes. If you did not request it, ignore this email. Never share this code.")
        try:
            context = ssl.create_default_context()
            client_connection = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=15, context=context) if self.settings.smtp_use_ssl else smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15)
            with client_connection as client:
                if not self.settings.smtp_use_ssl:
                    client.ehlo()
                    if self.settings.smtp_use_tls: client.starttls(context=context); client.ehlo()
                if self.settings.smtp_username: client.login(self.settings.smtp_username, self.settings.smtp_password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Verification email delivery failed") from exc
