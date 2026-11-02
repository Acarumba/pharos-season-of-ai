from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.policy_gatekeeper import Decision, PolicyGatekeeper

from .mock_executor import MockExecutor


ADDRESS = "0x1111111111111111111111111111111111111111"
CONTRACT = "0x2222222222222222222222222222222222222222"
SCENARIOS = {
    "Allowed request": {
        "amount": "10.00",
        "address": ADDRESS,
        "contract": CONTRACT,
        "trusted_now": "2026-11-01T10:00:00+00:00",
    },
    "Spend-limit violation": {
        "amount": "150.00",
        "address": ADDRESS,
        "contract": CONTRACT,
        "trusted_now": "2026-11-01T10:00:00+00:00",
    },
    "Address allowlist violation": {
        "amount": "10.00",
        "address": "0x3333333333333333333333333333333333333333",
        "contract": CONTRACT,
        "trusted_now": "2026-11-01T10:00:00+00:00",
    },
    "Time-window violation": {
        "amount": "10.00",
        "address": ADDRESS,
        "contract": CONTRACT,
        "trusted_now": "2026-11-01T18:00:00+00:00",
    },
}
RULES = ("spend_limit", "address_allowlist", "contract_allowlist", "time_window")


@dataclass
class SimulationResult:
    request: dict[str, Any]
    decision: Decision
    execution_result: Any
    executor_calls: int
    audit_entries: list[dict[str, Any]]


def load_policy(policy_path: Path) -> dict[str, Any]:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def run_scenario(package_dir: Path, scenario_name: str, request_id: str = "demo-001") -> SimulationResult:
    scenario = SCENARIOS[scenario_name]
    trusted_now = datetime.fromisoformat(scenario["trusted_now"])
    return run_request(
        package_dir,
        {
            "request_id": request_id,
            "amount": scenario["amount"],
            "address": scenario["address"],
            "contract": scenario["contract"],
        },
        trusted_now,
    )


def run_request(
    package_dir: Path, request: dict[str, Any], trusted_now: datetime
) -> SimulationResult:
    """Run a request through the real gatekeeper with a deterministic demo clock."""
    request = {
        "request_id": request["request_id"],
        "amount": request["amount"],
        "address": request["address"],
        "contract": request["contract"],
    }
    with tempfile.TemporaryDirectory(prefix="pharos-gatekeeper-demo-") as temp_dir:
        audit_path = Path(temp_dir) / "audit.jsonl"
        gatekeeper = PolicyGatekeeper.from_policy_file(
            package_dir / "policy.json",
            audit_path,
            clock=lambda: trusted_now,
        )
        executor = MockExecutor()
        decision, execution_result = gatekeeper.execute(request, executor)
        audit_entries = [
            json.loads(line)
            for line in audit_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    return SimulationResult(
        request=request,
        decision=decision,
        execution_result=execution_result,
        executor_calls=len(executor.calls),
        audit_entries=audit_entries,
    )


def rule_statuses(decision: Decision) -> dict[str, bool]:
    violations = {violation.split(":", 1)[0] for violation in decision.violations}
    return {rule: rule not in violations for rule in RULES}