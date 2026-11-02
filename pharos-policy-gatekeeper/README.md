# Pharos Policy Gatekeeper

Standalone policy gate for actions that an agent may pass to the Pharos Skill Engine command layer.

## Files

- `policy.json`: example policy configuration.
- `policy.schema.json`: JSON Schema for policy files.
- `src/policy_gatekeeper.py`: policy evaluation, execution boundary, and audit logging.
- `test/test_policy_gatekeeper.py`: unit tests using a mock executor.
- `demo/`: reviewer-facing Streamlit simulation using the existing `PolicyGatekeeper`.

## Policy schema

Every policy file contains:

```json
{
  "spend_limit": "100.00",
  "allowlist": {
    "addresses": ["0x..."],
    "contracts": ["0x..."]
  },
  "time_window": {
    "timezone": "UTC",
    "start": "09:00",
    "end": "17:00"
  }
}
```

`spend_limit` is a non-negative decimal string. Addresses and contracts are non-empty EVM address lists. The time window uses an IANA timezone and half-open, same-day semantics: `[start, end)`. The end time is excluded.

## Interface

```python
from src.policy_gatekeeper import PolicyGatekeeper

gatekeeper = PolicyGatekeeper.from_policy_file("policy.json", "audit.jsonl")
decision, result = gatekeeper.execute(request, executor)
```

Requests require `request_id`, `amount`, `address`, and `contract`. An optional `requested_at` field is validated as metadata but never controls enforcement. The policy window uses the gatekeeper's trusted clock; tests can inject a timezone-aware clock through `clock=`. Every decision is appended to the audit JSONL file before an allowed request reaches `executor`. A denied request returns without calling it. Malformed policy files and audit-write failures fail closed.

The official Pharos Skill Engine is an agent instruction package that eventually runs `cast` or `forge`; it does not expose a Python runtime API. This gate belongs before that command executor. This project does not sign or broadcast real transactions.

## Local demo

The Streamlit demo is a local simulation. It uses the existing `PolicyGatekeeper`, a temporary audit log, and a mock executor; it never signs, broadcasts, or calls the network. Presets cover an allowed request, spend-limit denial, address allowlist denial, and time-window denial. Denied scenarios visibly show the deciding rule and zero executor calls.

From this directory:

```powershell
python -m pip install -r demo\requirements.txt
streamlit run demo\app.py
```

Open the displayed local URL, choose a preset or **Custom request**, and click **Evaluate request**. Custom amount, address, and contract fields are mapped into the same request shape used by `PolicyGatekeeper`; deliberately malformed values are denied by the real validator and show zero mock executor calls. The trusted demo clock is injected separately so reviewers can demonstrate the time-window rule without making caller timestamps authoritative. The app shows the active policy, request, rule status, decision, execution counter, and audit entry.

## Tests

```powershell
python -m unittest discover -s test -v
```