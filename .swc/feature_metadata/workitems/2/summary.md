# Summary — 2: Bump version to 1.2.0 and surface via --version

## Outcome

Work item complete. All three sub-items (2.1, 2.2, 2.3) implemented and marked done in the workload. Full suite green (101/101). Manual `--version` and `-v` both emit bare `1.2.0`.

## Changes

- `swc_workload/_version.py` — `__version__` bumped from `"1.1.3"` to `"1.2.0"`.
- `swc_workload/cli.py` — in `build_parser()`, `--version` action's `version=` changed from `f"%(prog)s {__version__}"` to `f"{__version__}"`. Matches the `cli-change-spec.md` contract that the downstream `swc-workload-mcp` shells out and parses directly.
- `tests/e2e/test_swc-workload_help.py` — added `test_version_flag_outputs_bare_pinned_string`. Asserts `--version` and `-v` stripped stdout equal the literal `"1.2.0"` (not via `__version__` substring) so a future regression on either the bump or the bare-format is caught. Existing substring tests left in place; they continue to pass under the new format.

## Testing

- `uv run pytest tests/` — 101 passed, 0 failed, 15.20s. Matches `pipeline.md` build expectation.
- `uv run pytest tests/e2e/test_swc-workload_help.py -v` — 7 passed, including the new pinning test.
- Manual: `python -m swc_workload --version` and `... -v` both emit `1.2.0` and exit 0.

## Pipeline

- **Build:** `uv run pytest tests/` exit 0, all 101 tests pass.
- **Dev environment:** N/A (no long-running server).
- **Acceptance:** full suite green and `swc-workload --version` reports `1.2.0` — both confirmed.

## Build confidence

High. Three-line code/test change, pinning e2e covers both the version literal and the bare-format, full suite green, manual smoke confirms the contract.

## Scope flags

- README.md lines 60 and 63 reference `@v1.1.3` in install-example snippets. **Not updated** — requirements.md explicitly parked CHANGELOG / release notes to work item 7, and these example install tags belong with that release-docs surface. Flagged for the work-item-7 doc commit.

## Approach needs revisiting

No. The lightweight approach in `solution.md` held throughout.

## Files touched

- `swc_workload/_version.py`
- `swc_workload/cli.py`
- `tests/e2e/test_swc-workload_help.py`
- `.swc/feature_metadata/workitems/2/context.md` (created — pass 1 entries)
