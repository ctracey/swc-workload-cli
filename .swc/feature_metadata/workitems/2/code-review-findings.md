# Code Review Findings — 2: Bump version to 1.2.0 and surface via --version — 2026-06-04

## Summary

A tight, well-scoped three-line change that lands the version bump and the bare-format `--version` contract together. The implementation matches `solution.md` exactly: `_version.py` carries the canonical bump, `cli.py:build_parser()` drops the `%(prog)s` prefix from the argparse `version=` template, and a new pinning e2e test asserts the literal stripped output equals `"1.2.0"` for both `--version` and `-v`. The pinning test is correctly written against a literal string rather than `__version__`, which preserves its regression-catching value through future bumps — exactly as the solution doc reasons. All acceptance criteria from `specs.md` are satisfied: bare output, exit 0, short-form parity, literal-string pin, and existing substring tests continue to pass under the new format. No code-quality, SOLID, security, or traceability concerns surfaced.

## Findings

None.

## Verdict

**PASS**

Clean, minimal, spec-aligned change with a regression-pinning test; nothing to flag.
