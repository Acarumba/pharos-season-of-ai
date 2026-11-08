from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage

from .decoder import TransferEvent, format_amount
from .rules import AlertRule
from .storage import Storage


@dataclass(frozen=True)
class NotificationResult:
    status: str
    detail: str = ""


class TelegramNotifier:
    def __init__(self, storage: Storage, token: str | None = None, chat_id: str | None = None, timeout: float = 15) -> None:
        self.storage = storage
        self.token = token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID", "")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def format_message(self, event: TransferEvent, rule: AlertRule, decimals: int) -> str:
        timestamp = f"\nTimestamp: {event.timestamp}" if event.timestamp is not None else ""
        return (
            f"Pharos Alert: {rule.name}\n"
            f"Token: {event.token}\n"
            f"Amount: {format_amount(event.amount_raw, decimals)}\n"
            f"From: {event.sender}\nTo: {event.recipient}\n"
            f"Transaction: {event.transaction_hash}\nBlock: {event.block_number}{timestamp}\n"
            "Explorer: unavailable until the official URL is configured"
        )

    def send(self, event: TransferEvent, rule: AlertRule, decimals: int) -> NotificationResult:
        if not self.configured:
            result = NotificationResult("unavailable", "Telegram credentials are not configured")
            self.storage.record_notification(event.event_id, rule.name, result.status, result.detail)
            return result
        message = self.format_message(event, rule, decimals)
        payload = urllib.parse.urlencode({"chat_id": self.chat_id, "text": message}).encode()
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
            if not body.get("ok"):
                raise RuntimeError(str(body))
            result = NotificationResult("delivered", "Telegram confirmed delivery")
        except Exception as exc:
            result = NotificationResult("failed", str(exc))
        self.storage.record_notification(event.event_id, rule.name, result.status, result.detail)
        return result

    def test_notification(self) -> NotificationResult:
        if not self.configured:
            return NotificationResult("unavailable", "Telegram credentials are not configured")
        payload = urllib.parse.urlencode({"chat_id": self.chat_id, "text": "Pharos Alert Watch test notification"}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/sendMessage", data=payload, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
            return NotificationResult("delivered", "Telegram confirmed delivery") if body.get("ok") else NotificationResult("failed", str(body))
        except Exception as exc:
            return NotificationResult("failed", str(exc))


class EmailNotifier:
    def __init__(self, storage: Storage, recipient: str = "", timeout: float = 15) -> None:
        self.storage = storage
        self.recipient = recipient.strip()
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.sender = os.getenv("SMTP_FROM", self.username)
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.recipient and self.host and self.sender)

    def send(self, event: TransferEvent, rule: AlertRule, decimals: int) -> NotificationResult:
        if not self.configured:
            result = NotificationResult("unavailable", "SMTP settings or recipient email are missing")
            self.storage.record_notification(event.event_id, rule.name, "email_unavailable", result.detail)
            return result
        message = EmailMessage()
        message["Subject"] = f"Pharos Alert: {rule.name}"
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content(TelegramNotifier(self.storage).format_message(event, rule, decimals))
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.starttls(context=context)
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            result = NotificationResult("delivered", "SMTP server accepted the message")
        except Exception as exc:
            result = NotificationResult("failed", str(exc))
        self.storage.record_notification(event.event_id, rule.name, f"email_{result.status}", result.detail)
        return result

    def test_notification(self) -> NotificationResult:
        if not self.configured:
            return NotificationResult("unavailable", "SMTP settings or recipient email are missing")
        message = EmailMessage()
        message["Subject"] = "Pharos Alert Watch test notification"
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content("Pharos Alert Watch email delivery is configured.")
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                server.starttls(context=ssl.create_default_context())
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(message)
            return NotificationResult("delivered", "SMTP server accepted the message")
        except Exception as exc:
            return NotificationResult("failed", str(exc))


class NotificationRouter:
    def __init__(self, storage: Storage, email_recipient: str = "") -> None:
        self.telegram = TelegramNotifier(storage)
        self.email = EmailNotifier(storage, email_recipient)

    def send(self, event: TransferEvent, rule: AlertRule, decimals: int) -> str:
        results = []
        if self.telegram.configured:
            results.append(f"telegram:{self.telegram.send(event, rule, decimals).status}")
        if self.email.configured or self.email.recipient:
            results.append(f"email:{self.email.send(event, rule, decimals).status}")
        if not results:
            self.telegram.storage.record_notification(event.event_id, rule.name, "unavailable", "No notification channel is configured")
            return "unavailable"
        return ", ".join(results)
