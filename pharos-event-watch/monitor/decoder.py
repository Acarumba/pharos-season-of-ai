from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from eth_hash.auto import keccak

TRANSFER_SIGNATURE = "Transfer(address,address,uint256)"
TRANSFER_TOPIC = "0x" + keccak(TRANSFER_SIGNATURE.encode()).hex()


@dataclass(frozen=True)
class TransferEvent:
    event_key: str
    transaction_hash: str
    block_number: int
    log_index: int
    sender: str
    recipient: str
    raw_amount: int
    amount: str
    timestamp: int | None


def event_signature_topic(signature: str) -> str:
    if not signature or "(" not in signature:
        raise ValueError("event signature must be a non-empty Solidity signature")
    return "0x" + keccak(signature.encode()).hex()


def _hex_int(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16) if value.startswith("0x") else int(value)
        except ValueError as exc:
            raise ValueError(f"{field} is not an integer") from exc
    raise ValueError(f"{field} is not an integer")


def _word(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) != 66:
        raise ValueError(f"{field} must be a 32-byte hex word")
    try:
        int(value[2:], 16)
    except ValueError as exc:
        raise ValueError(f"{field} contains invalid hexadecimal") from exc
    return value


def _address(word: object, field: str) -> str:
    return "0x" + _word(word, field)[-40:]


def _format_units(value: int, decimals: int) -> str:
    return format(Decimal(value).scaleb(-decimals), "f").rstrip("0").rstrip(".") or "0"


def decode_transfer_log(log: dict, decimals: int = 6, timestamp: int | None = None) -> TransferEvent:
    if not isinstance(log, dict):
        raise ValueError("log must be an object")
    topics = log.get("topics")
    if not isinstance(topics, list) or len(topics) < 3:
        raise ValueError("Transfer log must contain three topics")
    if _word(topics[0], "topic0").lower() != TRANSFER_TOPIC:
        raise ValueError("log topic0 is not the Transfer event topic")
    sender = _address(topics[1], "from topic")
    recipient = _address(topics[2], "to topic")
    data = log.get("data", "0x")
    raw_amount = _hex_int(data, "data")
    if raw_amount < 0:
        raise ValueError("amount must be non-negative")
    transaction_hash = log.get("transactionHash") or log.get("transaction_hash")
    if not isinstance(transaction_hash, str) or not transaction_hash.startswith("0x"):
        raise ValueError("log is missing transaction hash")
    block_number = _hex_int(log.get("blockNumber"), "blockNumber")
    log_index = _hex_int(log.get("logIndex"), "logIndex")
    event_key = f"{transaction_hash.lower()}:{log_index}"
    return TransferEvent(event_key, transaction_hash, block_number, log_index, sender, recipient,
                         raw_amount, _format_units(raw_amount, decimals), timestamp)
