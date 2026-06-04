# Specs — 2: Bump version to 1.2.0 and surface via --version

## Acceptance criteria

- `swc_workload/_version.py` exports `__version__ = "1.2.0"`.
- `swc-workload --version` exits 0 and writes a **single bare version string** to stdout. Stripped, the output equals exactly `"1.2.0"` — no `swc workload ` prefix, no other tokens. This is the cli-change-spec.md contract the MCP relies on.
- `swc-workload -v` (short form) behaves identically to `--version`.
- An e2e test pins the exact stripped output `== "1.2.0"` (not just substring containment), so a regression on either the version bump or the bare-format change is caught.
- Full test suite stays green — existing tests in `test_swc-workload_help.py` use substring containment on `__version__` and continue to pass under the new format.

## Error cases

- None. This is a string and format change; there are no failure modes to assert.
