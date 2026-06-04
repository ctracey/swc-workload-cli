# Context — 2: Bump version to 1.2.0 and surface via --version

## Pass 1 — 2026-06-04

- **Test approach:** Lightweight — implemented directly against spec checklist, then added the pinning test, per `solution.md`.
- **Change 1 (cli.py):** `build_parser()` `--version` action `version=f"%(prog)s {__version__}"` → `version=f"{__version__}"` so output is bare, matching the cli-change-spec contract the MCP reads.
- **Change 2 (_version.py):** `__version__` `"1.1.3"` → `"1.2.0"`.
- **Change 3 (tests/e2e/test_swc-workload_help.py):** added `test_version_flag_outputs_bare_pinned_string` asserting `--version` and `-v` stripped stdout equal the literal `"1.2.0"` — not `__version__` — so a future bump or format regression is caught. Existing `__version__`-substring tests left intact (they pass under the new format too).
- **Decision:** Did NOT touch README `@v1.1.3` install-example tags or any CHANGELOG. Requirements explicitly park release notes to work item 7 so the metadata feature lands in one cohesive doc commit.
- **Verified:** `uv run python -m swc_workload --version` and `... -v` both emit `1.2.0`. Full suite green (101/101).
