from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from alert_engine.decoder import TRANSFER_TOPIC, decode_transfer_log
from alert_engine.monitor import Monitor
from alert_engine.notifications import EmailNotifier, TelegramNotifier
from alert_engine.rules import AlertRule, parse_threshold, validate_address, validate_email
from alert_engine.storage import Storage

SENDER = "0x" + "11" * 20
RECIPIENT = "0x" + "22" * 20

def transfer(amount: int = 2_000_000, tx: str = "0xabc") -> dict:
    return {"address": "0x" + "aa" * 20, "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + SENDER[2:], "0x" + "0" * 24 + RECIPIENT[2:]], "data": f"0x{amount:064x}", "transactionHash": tx, "blockNumber": "0x10", "logIndex": "0x0"}

class Client:
    def __init__(self): self.calls = 0
    def token_decimals(self, _): return 6
    def block_number(self): self.calls += 1; return 16
    def logs(self, *_): return [transfer()]

def test_decode_and_rules():
    event = decode_transfer_log(transfer())
    assert event.amount_raw == 2_000_000 and event.sender == SENDER
    assert AlertRule("big", threshold_raw=parse_threshold("1.5", 6)).matches(event)
    assert AlertRule("sender", sender=SENDER).matches(event)
    assert AlertRule("recipient", recipient=RECIPIENT).matches(event)

def test_multiple_rules_and_dedup(tmp_path: Path):
    storage = Storage(str(tmp_path / "a.sqlite3")); client = Client()
    rules = [AlertRule("big", threshold_raw=1_000_000), AlertRule("from", sender=SENDER), AlertRule("off", enabled=False)]
    monitor = Monitor(client, storage, "0x" + "aa" * 20, rules)
    assert len(monitor.poll_once()) == 2
    assert monitor.poll_once() == []
    assert storage.get_checkpoint("transfer") == 16

def test_disabled_event_type_skips_chain_poll(tmp_path: Path):
    storage = Storage(str(tmp_path / "a.sqlite3")); client = Client()
    monitor = Monitor(client, storage, "0x" + "aa" * 20, [], enabled_event_types=set())
    assert monitor.poll_once() == []
    assert client.calls == 0

def test_validation():
    with pytest.raises(ValueError): validate_address("nope")
    with pytest.raises(ValueError): parse_threshold("1.0000001", 6)
    assert validate_email("alerts@example.com") == "alerts@example.com"
    with pytest.raises(ValueError): validate_email("not-an-email")

def test_failed_query_does_not_advance_checkpoint(tmp_path: Path):
    class Broken(Client):
        def block_number(self): raise RuntimeError("temporary")
    storage = Storage(str(tmp_path / "a.sqlite3")); monitor = Monitor(Broken(), storage, "0x" + "aa" * 20, [])
    with pytest.raises(RuntimeError): monitor.poll_once()
    assert storage.get_checkpoint("transfer") == 0

def test_telegram_success_failure_and_missing_config(tmp_path: Path):
    storage = Storage(str(tmp_path / "a.sqlite3")); event = decode_transfer_log(transfer()); rule = AlertRule("big")
    missing = TelegramNotifier(storage, "", "")
    assert missing.send(event, rule, 6).status == "unavailable"
    with patch("urllib.request.urlopen") as request:
        request.return_value.__enter__.return_value.read.return_value = json.dumps({"ok": True}).encode()
        assert TelegramNotifier(storage, "token", "chat").send(event, rule, 6).status == "delivered"
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert TelegramNotifier(storage, "token", "chat").send(event, rule, 6).status == "failed"

def test_email_missing_and_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    storage = Storage(str(tmp_path / "a.sqlite3")); event = decode_transfer_log(transfer()); rule = AlertRule("big")
    assert EmailNotifier(storage, "alerts@example.com").send(event, rule, 6).status == "unavailable"
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "bot@example.com")
    with patch("smtplib.SMTP") as smtp:
        assert EmailNotifier(storage, "alerts@example.com").send(event, rule, 6).status == "delivered"
