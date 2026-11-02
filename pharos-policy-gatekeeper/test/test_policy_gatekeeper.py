import json
import tempfile
import unittest
from pathlib import Path

from src.policy_gatekeeper import AuditError, PolicyError, PolicyGatekeeper


ADDRESS = "0x1111111111111111111111111111111111111111"
CONTRACT = "0x2222222222222222222222222222222222222222"
REQUEST = {
    "request_id": "req-1",
    "amount": "10.00",
    "address": ADDRESS,
    "contract": CONTRACT,
    "requested_at": "2026-11-01T10:00:00+00:00",
}
POLICY = {
    "spend_limit": "100.00",
    "allowlist": {"addresses": [ADDRESS], "contracts": [CONTRACT]},
    "time_window": {"timezone": "UTC", "start": "09:00", "end": "17:00"},
}


class PolicyGatekeeperTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_path = Path(self.temp_dir.name) / "audit.jsonl"
        self.gatekeeper = PolicyGatekeeper(POLICY, self.audit_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_rules_pass_and_executor_runs_once(self):
        calls = []
        decision, result = self.gatekeeper.execute(REQUEST, lambda request: calls.append(request) or "done")
        self.assertEqual(decision.outcome, "allow")
        self.assertEqual(decision.deciding_rule, "all_rules_pass")
        self.assertEqual(result, "done")
        self.assertEqual(len(calls), 1)

    def test_spend_limit_deny(self):
        decision, result = self.gatekeeper.execute({**REQUEST, "amount": "100.01"}, lambda _: self.fail())
        self.assertEqual((decision.outcome, decision.deciding_rule), ("deny", "spend_limit"))
        self.assertIsNone(result)

    def test_address_allowlist_deny(self):
        decision, result = self.gatekeeper.execute({**REQUEST, "address": "0x333"}, lambda _: self.fail())
        self.assertEqual((decision.outcome, decision.deciding_rule), ("deny", "address_allowlist"))
        self.assertIsNone(result)

    def test_contract_allowlist_deny(self):
        decision, result = self.gatekeeper.execute({**REQUEST, "contract": "0x444"}, lambda _: self.fail())
        self.assertEqual((decision.outcome, decision.deciding_rule), ("deny", "contract_allowlist"))
        self.assertIsNone(result)

    def test_time_window_deny_and_boundary_is_exclusive(self):
        decision, result = self.gatekeeper.execute(
            {**REQUEST, "requested_at": "2026-11-01T17:00:00Z"}, lambda _: self.fail()
        )
        self.assertEqual((decision.outcome, decision.deciding_rule), ("deny", "time_window"))
        self.assertIsNone(result)

    def test_multiple_violations_are_all_reported(self):
        request = {
            **REQUEST,
            "amount": "101",
            "address": "0x333",
            "contract": "0x444",
            "requested_at": "2026-11-01T18:00:00Z",
        }
        decision, result = self.gatekeeper.execute(request, lambda _: self.fail())
        self.assertEqual(decision.outcome, "deny")
        self.assertEqual(len(decision.violations), 4)
        self.assertIsNone(result)

    def test_malformed_input_denies_and_is_audited(self):
        decision, result = self.gatekeeper.execute({"request_id": "bad"}, lambda _: self.fail())
        self.assertEqual((decision.outcome, decision.deciding_rule), ("deny", "input"))
        self.assertIsNone(result)
        self.assertEqual(len(self.audit_path.read_text(encoding="utf-8").splitlines()), 1)

    def test_every_decision_is_audit_logged(self):
        self.gatekeeper.evaluate(REQUEST)
        self.gatekeeper.evaluate({**REQUEST, "amount": "101"})
        entries = [json.loads(line) for line in self.audit_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([entry["outcome"] for entry in entries], ["allow", "deny"])
        self.assertEqual(entries[1]["request_id"], "req-1")
        self.assertIn("spend_limit", entries[1]["violations"][0])

    def test_audit_failure_fails_closed(self):
        gatekeeper = PolicyGatekeeper(POLICY, Path(self.temp_dir.name) / "audit-dir")
        (Path(self.temp_dir.name) / "audit-dir").mkdir()
        with self.assertRaises(AuditError):
            gatekeeper.execute(REQUEST, lambda _: self.fail())

    def test_malformed_policy_fails_closed_at_load(self):
        with self.assertRaises(PolicyError):
            PolicyGatekeeper({"spend_limit": "not-a-number"}, self.audit_path)

    def test_policy_file_is_loaded(self):
        policy_path = Path(self.temp_dir.name) / "policy.json"
        policy_path.write_text(json.dumps(POLICY), encoding="utf-8")
        gatekeeper = PolicyGatekeeper.from_policy_file(policy_path, self.audit_path)
        decision = gatekeeper.evaluate(REQUEST)
        self.assertEqual(decision.outcome, "allow")


if __name__ == "__main__":
    unittest.main()