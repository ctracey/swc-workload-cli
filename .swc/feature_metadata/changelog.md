# Changelog

## Session — work item 3: meta field foundation `2026-06-04`

- Added `swc_workload/meta.py` with two stateless helpers used across phases 3–6: `parse_bool_flag` (strict casefolded `true`/`false` → `bool`, else `CLIError`) and `parse_meta_json` (JSON-object parser with split error messages for parse-fail vs non-object). Scaffolds the shared `--meta` / `--ids` parser the later items 5/6 import from.
- Extended `swc_workload/io.py::_validate_shape` with an optional `meta` check: absent loads (legacy artefacts), present-but-not-dict fails with the existing JSON-path error format. REQ-05 (read tolerance) and REQ-10 (shape pin) both anchored here.
- Wired `--meta <json>` into `AddCommand`: parsed up front so error paths never touch `workload.json`; new nodes always built with `"meta": meta` (default `{}` when the flag is omitted). `add --json` output shape intentionally unchanged — `meta` echo lands with the read-flag work in item 5.
- No code changes to `rename` / `delete` / `move` / `start` / `complete` / `reset` — `meta` rides along through existing dict-in-place mutations. Sub-item 3.5 is a defensive pin only.
- Tests: +26 unit (`test_meta.py`), +8 unit (`test_validate_shape_meta.py`), +24 e2e (`test_swc-workload_meta.py`). Suite now 159 passing (was 101). Pre-existing pin `test_add_json_emits_id_title_status` still green.
- Motivation: unblocks items 4 (new subcommands) and 5/6 (changed reads + atomic transitions) — both depend on the `meta` field existing on items and the shared bool parser being importable.

## Session — work item 2: bump to 1.2.0 + bare --version `2026-06-04`

- Bumped `swc_workload/_version.py` from `1.1.3` to `1.2.0`. Minor bump per README §Versioning — the upcoming `meta` field is additive on `workload.json`, so the on-disk shape stays backwards-compatible.
- Changed `swc_workload/cli.py:build_parser()` so `--version` (and `-v`) emit a bare version string (`1.2.0`) instead of the argparse default `swc workload 1.2.0`. Matches the `cli-change-spec.md` contract the downstream `swc-workload-mcp` shells out to.
- Added `test_version_flag_outputs_bare_pinned_string` in `tests/e2e/test_swc-workload_help.py` — pins the exact stripped output to the literal `"1.2.0"` (not via `__version__` substring) so a future regression on either the bump or the bare-format is caught.
- Motivation: gating commit for the metadata feature. The MCP can pin `>=1.2.0` and start its integration work in parallel with items 3–7.
