from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


Clock = Callable[[], datetime]
EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


class PolicyError(ValueError):
    pass


class AuditError(RuntimeError):
    pass


@dataclass(frozen=True)
class Decision:
    request_id: str
    outcome: str
    deciding_rule: str
    reason: str
    violations: tuple[str, ...]
    timestamp: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "outcome": self.outcome,
            "deciding_rule": self.deciding_rule,
            "reason": self.reason,
            "violations": list(self.violations),
            "timestamp": self.timestamp,
        }


class PolicyGatekeeper:
    """Evaluates requests and owns the only path to a supplied executor."""

    def __init__(
        self,
        policy: Mapping[str, Any],
        audit_path: str | os.PathLike[str],
        clock: Clock | None = None,
    ):
        self._policy = _validate_policy(policy)
        self._audit_path = Path(audit_path)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def from_policy_file(
        cls,
        policy_path: str | os.PathLike[str],
        audit_path: str | os.PathLike[str],
        clock: Clock | None = None,
    ) -> "PolicyGatekeeper":
        try:
            with Path(policy_path).open(encoding="utf-8") as policy_file:
                policy = json.load(policy_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f"cannot load policy: {exc}") from exc
        return cls(policy, audit_path, clock=clock)

    def evaluate(self, request: Mapping[str, Any]) -> Decision:
        trusted_now = self._trusted_now()
        timestamp = trusted_now.isoformat()
        request_id = request.get("request_id", "<missing>") if isinstance(request, Mapping) else "<malformed>"
        if not isinstance(request_id, str) or not request_id:
            request_id = "<invalid>"

        violations: list[str] = []
        try:
            normalized = _validate_request(request)
            violations.extend(self._rule_violations(normalized, trusted_now))
        except (PolicyError, TypeError) as exc:
            violations.append(f"input: {exc}")

        outcome = "deny" if violations else "allow"
        deciding_rule = violations[0].split(":", 1)[0] if violations else "all_rules_pass"
        reason = violations[0] if violations else "all policy rules passed"
        decision = Decision(request_id, outcome, deciding_rule, reason, tuple(violations), timestamp)
        self._write_audit(decision)
        return decision

    def execute(
        self, request: Mapping[str, Any], executor: Callable[[Mapping[str, Any]], Any]
    ) -> tuple[Decision, Any | None]:
        decision = self.evaluate(request)
        if decision.outcome == "deny":
            return decision, None
        return decision, executor(request)

    def _rule_violations(self, request: dict[str, Any], trusted_now: datetime) -> list[str]:
        policy = self._policy
        violations: list[str] = []
        if request["amount"] > policy["spend_limit"]:
            violations.append(
                f"spend_limit: amount {request['amount']} exceeds limit {policy['spend_limit']}"
            )

        allowlist = policy["allowlist"]
        if request["address"] not in allowlist["addresses"]:
            violations.append(f"address_allowlist: address {request['address']} is not allowed")
        if request["contract"] not in allowlist["contracts"]:
            violations.append(f"contract_allowlist: contract {request['contract']} is not allowed")

        window = policy["time_window"]
        request_time = trusted_now.astimezone(window["zone"]).time().replace(microsecond=0)
        start, end = window["start"], window["end"]
        if not start <= request_time < end:
            violations.append(
                f"time_window: {request_time.isoformat()} is outside [{start.isoformat()}, {end.isoformat()})"
            )
        return violations

    def _trusted_now(self) -> datetime:
        try:
            trusted_now = self._clock()
        except Exception as exc:
            raise PolicyError(f"trusted clock unavailable: {exc}") from exc
        if not isinstance(trusted_now, datetime) or trusted_now.tzinfo is None:
            raise PolicyError("trusted clock must return a timezone-aware datetime")
        return trusted_now

    def _write_audit(self, decision: Decision) -> None:
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self._audit_path.open("a", encoding="utf-8") as audit_file:
                audit_file.write(json.dumps(decision.as_dict(), sort_keys=True) + "\n")
                audit_file.flush()
                os.fsync(audit_file.fileno())
        except (OSError, TypeError, ValueError) as exc:
            raise AuditError(f"cannot write audit decision: {exc}") from exc


def _validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, Mapping):
        raise PolicyError("policy must be an object")
    try:
        spend_limit = _decimal(policy["spend_limit"], "spend_limit")
        if spend_limit < 0:
            raise PolicyError("spend_limit must be non-negative")
        allowlist = policy["allowlist"]
        addresses = _addresses(allowlist["addresses"], "allowlist.addresses")
        contracts = _addresses(allowlist["contracts"], "allowlist.contracts")
        window = policy["time_window"]
        zone = ZoneInfo(window["timezone"])
        start = _clock_time(window["start"], "time_window.start")
        end = _clock_time(window["end"], "time_window.end")
        if start >= end:
            raise PolicyError("time_window must be a same-day interval with start < end")
    except (KeyError, TypeError, ZoneInfoNotFoundError) as exc:
        raise PolicyError(f"malformed policy: {exc}") from exc
    return {
        "spend_limit": spend_limit,
        "allowlist": {"addresses": addresses, "contracts": contracts},
        "time_window": {"zone": zone, "start": start, "end": end},
    }


def _validate_request(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise PolicyError("request must be an object")
    required = ("request_id", "amount", "address", "contract")
    missing = [field for field in required if field not in request]
    if missing:
        raise PolicyError(f"missing required fields: {', '.join(missing)}")
    if not isinstance(request["request_id"], str) or not request["request_id"]:
        raise PolicyError("request_id must be a non-empty string")
    if "requested_at" in request:
        requested_at = request["requested_at"]
        if isinstance(requested_at, str):
            try:
                requested_at = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise PolicyError("requested_at must be an ISO-8601 timestamp") from exc
        if not isinstance(requested_at, datetime) or requested_at.tzinfo is None:
            raise PolicyError("requested_at must include a timezone")
    return {
        "amount": _decimal(request["amount"], "amount"),
        "address": _address(request["address"], "address"),
        "contract": _address(request["contract"], "contract"),
    }


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise PolicyError(f"{field} must be a decimal string, integer, or Decimal")
    if not isinstance(value, (str, int, Decimal)):
        raise PolicyError(f"{field} must be a decimal string, integer, or Decimal")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PolicyError(f"{field} must be a decimal string, integer, or Decimal") from exc
    if not result.is_finite() or result < 0:
        raise PolicyError(f"{field} must be finite and non-negative")
    return result


def _addresses(values: Any, field: str) -> frozenset[str]:
    if not isinstance(values, list) or not values:
        raise PolicyError(f"{field} must be a non-empty list")
    return frozenset(_address(value, field) for value in values)


def _address(value: Any, field: str) -> str:
    if not isinstance(value, str) or not EVM_ADDRESS.fullmatch(value):
        raise PolicyError(f"{field} must be a 0x-prefixed 40-hex-character EVM address")
    return value.lower()


def _clock_time(value: Any, field: str) -> time:
    if not isinstance(value, str):
        raise PolicyError(f"{field} must be HH:MM")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise PolicyError(f"{field} must be HH:MM") from exc
    if parsed.second or parsed.microsecond:
        raise PolicyError(f"{field} must be HH:MM")
    return parsed