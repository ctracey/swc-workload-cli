# Solution Design — 2: Bump version to 1.2.0 and surface via --version

## Approach

Three small changes landed together as one commit:

1. **`swc_workload/cli.py:build_parser()`** — change the `action="version"` argument's `version=` from `f"%(prog)s {__version__}"` to `f"{__version__}"`, so `--version` (and `-v`) emit a bare version string matching the cli-change-spec.md contract.
2. **`swc_workload/_version.py`** — bump `__version__` from `"1.1.3"` to `"1.2.0"`.
3. **`tests/e2e/test_swc-workload_help.py`** — add one new e2e test that asserts `swc-workload --version` output, when stripped, equals exactly `"1.2.0"` (literal-string match, not via `__version__` import). Optionally also assert the same for `-v`.

## Test approach

Lightweight — implement directly against the spec checklist, then add the pinning test. Scenario-driven TDD adds ceremony with no benefit for a three-line change. The existing version-flag tests in `test_swc-workload_help.py` continue to pass under the new format (they use `__version__` substring containment, which holds either way), so the suite stays green throughout.

## Technical decisions

- **Pin the literal string `"1.2.0"`, not `__version__`.** The whole point of the e2e is to catch a future accidental revert of either the bump or the format. Importing `__version__` for the assertion would self-update with any bump and defeat the purpose. The existing substring-containment tests already cover the "version is wired" property.
- **Don't fall back to argparse's `%(prog)s ` default in the test.** The cli-change-spec.md requires bare output; the assertion must use exact-equality on the stripped output to pin that, not substring containment (which would pass for the old format too).

## Notes

- `pyproject.toml` already points hatchling at `swc_workload/_version.py` — no build config change needed.
- `cli.py:build_parser()` has the `description=f"... (version {__version__})"` which embeds the version in `--help` output. Leave that alone; the existing `test_top_level_help_shows_version` test will pass with `1.2.0` substituted in.
