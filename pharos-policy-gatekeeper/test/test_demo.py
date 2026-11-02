import unittest
from pathlib import Path

from datetime import datetime, timezone

from demo.demo_logic import ADDRESS, CONTRACT, run_request, run_scenario


PACKAGE_DIR = Path(__file__).parents[1]


class DemoScenarioTests(unittest.TestCase):
    def test_custom_valid_request_is_allowed_and_executes_once(self):
        result = run_request(
            PACKAGE_DIR,
            {
                "request_id": "custom-001",
                "amount": "10.00",
                "address": ADDRESS,
                "contract": CONTRACT,
            },
            datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result.decision.outcome, "allow")
        self.assertEqual(result.executor_calls, 1)

    def test_custom_wrong_amount_is_denied_without_execution(self):
        result = run_request(
            PACKAGE_DIR,
            {
                "request_id": "custom-002",
                "amount": "not-a-number",
                "address": ADDRESS,
                "contract": CONTRACT,
            },
            datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result.decision.outcome, "deny")
        self.assertEqual(result.decision.deciding_rule, "input")
        self.assertEqual(result.executor_calls, 0)

    def test_allowed_scenario_calls_mock_executor_once(self):
        result = run_scenario(PACKAGE_DIR, "Allowed request")
        self.assertEqual(result.decision.outcome, "allow")
        self.assertEqual(result.executor_calls, 1)
        self.assertEqual(result.audit_entries[0]["outcome"], "allow")

    def test_denied_scenarios_call_mock_executor_zero_times(self):
        for scenario in (
            "Spend-limit violation",
            "Address allowlist violation",
            "Time-window violation",
        ):
            with self.subTest(scenario=scenario):
                result = run_scenario(PACKAGE_DIR, scenario)
                self.assertEqual(result.decision.outcome, "deny")
                self.assertEqual(result.executor_calls, 0)
                self.assertEqual(result.audit_entries[0]["outcome"], "deny")

    def test_denied_scenarios_report_the_expected_rule(self):
        expected = {
            "Spend-limit violation": "spend_limit",
            "Address allowlist violation": "address_allowlist",
            "Time-window violation": "time_window",
        }
        for scenario, rule in expected.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(run_scenario(PACKAGE_DIR, scenario).decision.deciding_rule, rule)


if __name__ == "__main__":
    unittest.main()