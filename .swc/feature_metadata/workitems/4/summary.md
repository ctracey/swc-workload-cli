# Summary — 4: New subcommands — get, update-meta, find-by-meta

## Pass 1 — 2026-06-04

### Changes

- **`swc_workload/meta.py`** — extended with four pure helpers:
  - `parse_path(raw)` — splits a dotted path into a tuple; `""` → `()`; segments preserved verbatim (`:` is a literal character).
  - `read_at_path(meta, path)` — walks the meta dict; returns `(True, value)` for any present value (incl. falsy), `(False, None)` for missing intermediate / missing leaf / non-object intermediate. Empty path returns `(True, meta)`.
  - `write_at_path(meta, path, value)` — mutates in place; creates missing intermediate objects; raises `CLIError` on non-object intermediate or empty path.
  - `parse_meta_value(raw)` — `json.loads` wrapper that accepts any JSON type, with `CLIError` on parse failure. Used by `update-meta` at non-empty paths.
- **`swc_workload/commands/get_command.py`** (new) — `GetCommand`. Resolves ref via `find_by_ref`; emits a single JSON object (`render_item_json` + projected `meta`) when `--json`; text output uses `render_item_text`. `--meta true|false` controls inclusion of the `meta` key (default `true`). Legacy items project `meta: {}` without rewriting the file.
- **`swc_workload/commands/update_meta_command.py`** (new) — `UpdateMetaCommand`. Positionals `ref`, `path`, `json_value`. Empty path branches to `parse_meta_json` (object required) and replaces the whole `meta`; non-empty path uses `parse_meta_value` (any type) + `parse_path` + `write_at_path`. Value parsed before file load so error paths never write. JSON output is `{id, path, value}`; text output `[<id>] meta <path> updated`.
- **`swc_workload/commands/find_by_meta_command.py`** (new) — `FindByMetaCommand`. Single class handles presence + pattern modes (`pattern` is `nargs="?"`). Compiles regex up front so invalid patterns fail before any disk read. Walks `iter_items`, skips legacy items (no `meta` key) entirely (REQ-15). `--meta true|false` controls inclusion of the `meta` blob per match (default `false`). Output mirrors `find`: `{matches: [{id, number, title, status[, meta]}]}`.
- **`swc_workload/commands/__init__.py`** — registered `GetCommand` and `FindByMetaCommand` between `SummaryCommand` and `AddCommand` (read cluster); registered `UpdateMetaCommand` at the end (write cluster). Imports added in alphabetical order.
- **`.swc/feature_metadata/workitems/4/context.md`** — pass 1 created with decisions per sub-item.

### Testing

Full TDD per sub-item — red test first, implementation to green, then full-suite run for regressions. Five new test files added under `tests/unit/` and `tests/e2e/`:

- `tests/unit/test_meta_path.py` — drives the helpers directly: every row of REQ-16's example tables (`parse_path`, `read_at_path`, `write_at_path`) plus failure modes (`CLIError` on empty path / non-object intermediate) and `parse_meta_value` JSON-type coverage.
- `tests/e2e/test_swc-workload_get.py` — subprocess invocations against per-test workload folders. Covers REQ-01/02/03, REQ-15 (get half), REQ-17. Includes byte-snapshot checks that error and legacy-read paths never rewrite `workload.json`.
- `tests/e2e/test_swc-workload_update_meta.py` — every JSON leaf type, empty-path replace-with-object, intermediate creation, non-object intermediate refusal, malformed JSON, unknown ref, legacy item write-through. Each error scenario asserts byte-for-byte unchanged `workload.json`.
- `tests/e2e/test_swc-workload_find_by_meta_presence.py` — presence at every depth, falsy-value hits, empty-path matches every item with meta, legacy items always silent miss, `--meta` flag default-off + explicit toggle.
- `tests/e2e/test_swc-workload_find_by_meta_pattern.py` — anchored/unanchored regex on string leaves, silent skip of non-string leaves and missing paths, invalid regex error (with and without `--json`), `--meta` toggle.

Manual spot-checks: `swc-workload get --help`, `update-meta --help`, `find-by-meta --help` — usage lines and positional descriptions read naturally (per solution.md instruction).

### Test results

- New tests added in this work item: **119** (42 unit + 77 e2e).
- Full suite before: 159 passing. After: **278 passing, 0 failed** via `uv run pytest tests/`.
- Subset commands also green: `uv run pytest tests/unit/`, `uv run pytest tests/e2e/`.

### Pipeline

Pipeline.md defines `uv run pytest tests/` as the build command and `swc-workload --version` reporting `1.2.0` as the acceptance signal.

- `uv run pytest tests/` — exit 0, **278 passed in 26.36s**.
- `uv run swc-workload --version` — emits `1.2.0` (bare, unchanged from work item 2).

No dev environment to verify (console-script only, per pipeline.md).

### Build confidence

High. Strict TDD per sub-item means every requirement (REQ-01 through REQ-17 for the parts in scope here) has at least one failing-then-green test backing it. Pre-existing 159 tests untouched; 119 new tests slot in cleanly. Help text spot-checked for the three new commands.

One detail worth a reviewer's eye: `update-meta` text output (`[<id>] meta <path> updated`, with `<root>` for empty path) and JSON output (`{id, path, value}` with `path` echoing the input verbatim — empty string preserved) are not explicitly pinned by the spec — the shapes were chosen by solution.md's "decisions" section. Test pins now make them part of the contract.

### Scope flags

None. All five sub-items map directly to spec scenarios; no out-of-scope work surfaced.

### Approach needs revisiting

No.

---

## Pass 2 — 2026-06-06

### Changes

- **`swc_workload/meta.py`** — refactored `parse_meta_json` into a flag-agnostic core. Added `parse_meta_object(raw, *, label) -> dict` (keyword-only `label`) that produces error messages reading `<label> must be valid JSON: ...` / `<label> must be a JSON object, got <type>`. `parse_meta_json` is now a thin wrapper that pins `label="--meta"`, preserving the verbatim wording every `add --meta <json>` caller (and the MCP integration tests that grep for it) expects. Module docstring updated.
- **`swc_workload/commands/update_meta_command.py`** — empty-path branch switched from `parse_meta_json(args.value)` to `parse_meta_object(args.value, label="<json-value>")`. Error messages on `update-meta <ref> "" <json-value>` now correctly name the positional the user actually typed, not the `--meta` flag which does not exist on this command. Import line updated accordingly.
- **`.swc/feature_metadata/workitems/4/context.md`** — appended pass 2 decisions: option (b) chosen over (a), `parse_meta_object` named (not `_parse_json_object`) to advertise reuse by item 6, label is keyword-only, original loose substring assertions preserved alongside the new strict label assertions.

### Testing

Pass-2 fix targeted at code-review finding F-01 (warn). Strict TDD: wrote red tests first (import-error and stderr-grep failures), then implemented the refactor to green.

- `tests/unit/test_meta.py` — 3 new tests: `test_parse_meta_json_error_messages_keep_meta_flag_label` (pins backward-compat for `--meta` callers), `test_parse_meta_object_uses_supplied_label_in_errors` (covers both parse-failure and non-object failure modes with a custom label, asserts `--meta` absent), `test_parse_meta_object_returns_parsed_object` (happy path).
- `tests/e2e/test_swc-workload_update_meta.py` — 2 new tests: `test_update_meta_empty_path_non_object_error_names_json_value_positional` and `test_update_meta_empty_path_malformed_json_error_names_json_value_positional`. Both assert stderr contains `<json-value>` and does NOT contain `--meta`. Pre-existing `"object" in stderr.lower()` / `"json" in stderr.lower()` checks left in place — they still hold under the corrected message, so the loose contract stays covered.
- Smoke-tested via the installed `swc-workload` CLI in `/tmp` against a fresh workload: confirmed `update-meta 1 "" '"a string"'` emits `<json-value> must be a JSON object, got string`, and `add "x" --meta '"oops"'` still emits `--meta must be a JSON object, got string`. Labels routed correctly through the shared core.

### Test results

- New tests added in pass 2: **5** (3 unit + 2 e2e).
- Full suite before pass 2: 278 passing. After pass 2: **283 passing, 0 failed** via `uv run pytest tests/`.

### Pipeline

- `uv run pytest tests/` — exit 0, **283 passed in 25.74s**.
- `uv run swc-workload --version` — emits `1.2.0` (unchanged).
- Dev environment not applicable — console script only.

### Build confidence

High. The refactor is mechanical (`parse_meta_json` now delegates to `parse_meta_object`), all pre-existing callers preserved by the wrapper, and the new label-aware path is covered by both unit tests (asserting label routing) and e2e tests (asserting end-to-end stderr against the real CLI). Item 6 will reuse `parse_meta_object` directly for `start`/`complete`/`reset` `--meta <json>` parsing — the keyword-only `label` argument signals the intended call site.

### Scope flags

None. The fix is contained to F-01; the four info-level findings from the code review (F-02 child meta projection, F-03 match-entry render duplication, F-04 root-by-reference, F-05 write_at_path ordering) were explicitly not in scope for this pass and remain unaddressed.

### Approach needs revisiting

No.
