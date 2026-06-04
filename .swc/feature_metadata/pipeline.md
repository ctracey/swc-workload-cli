# Pipeline

## Build

**Command:** `uv run pytest tests/`
**Expected outcome:** exit 0, all tests pass. Subset commands match CI:
- `uv run pytest tests/unit/`
- `uv run pytest tests/e2e/`

## Dev environment

**Start command:** not applicable — `swc-workload` is a console script, no long-running dev server.
**Health check:** not applicable.
**Stop command:** not applicable.

## Acceptance

- Full test suite (unit + e2e) green via `uv run pytest tests/`.
- `swc-workload --version` reports `1.2.0`.
