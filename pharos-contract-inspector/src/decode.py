from __future__ import annotations

from decimal import Decimal


def decode_uint256(result: str) -> int:
    if len(result) != 66 or not result.startswith("0x"):
        raise ValueError("expected a single uint256 ABI result")
    try:
        return int(result[2:], 16)
    except ValueError as exc:
        raise ValueError("uint256 result contains invalid hexadecimal") from exc


def decode_string(result: str) -> str:
    if not result.startswith("0x") or len(result) < 130:
        raise ValueError("expected an ABI-encoded string result")
    try:
        payload = bytes.fromhex(result[2:])
        offset = int.from_bytes(payload[:32], "big")
        length = int.from_bytes(payload[offset : offset + 32], "big")
        end = offset + 32 + length
        if end > len(payload):
            raise ValueError("malformed ABI string length")
        return payload[offset + 32 : end].decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("malformed ABI string result") from exc


def format_units(value: int, decimals: int) -> str:
    if decimals < 0:
        raise ValueError("decimals must be non-negative")
    return format(Decimal(value) / (Decimal(10) ** decimals), "f").rstrip("0").rstrip(".") or "0"