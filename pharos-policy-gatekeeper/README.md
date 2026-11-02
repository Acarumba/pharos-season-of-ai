# Pharos Policy Gatekeeper

Standalone policy gate for actions that an agent may pass to the Pharos Skill Engine command layer.

## Files

- `policy.json`: example policy configuration.
- `policy.schema.json`: JSON Schema for policy files.
- `src/policy_gatekeeper.py`: policy evaluation, execution boundary, and audit logging.
- `test/test_policy_gatekeeper.py`: unit tests using a mock executor.

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

Requests require `request_id`, `amount`, `address`, `contract`, and a timezone-aware ISO-8601 `requested_at`. Every decision is appended to the audit JSONL file before an allowed request reaches `executor`. A denied request returns without calling it. Malformed policy files and audit-write failures fail closed.

The official Pharos Skill Engine is an agent instruction package that eventually runs `cast` or `forge`; it does not expose a Python runtime API. This gate belongs before that command executor. This project does not sign or broadcast real transactions.

## Tests

```powershell
python -m unittest discover -s test -v
```