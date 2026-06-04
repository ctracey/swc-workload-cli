# Summary — 3: meta field foundation — default {}, read tolerance, add --meta <json>

## Pass 1 — 2026-06-04

### Changes

- **New module `swc_workload/meta.py`** — houses two stateless helpers used by 1.2.0 meta work:
  - `parse_bool_flag(value: str) -> bool` — strict casefolded match against `"true"` / `"false"`; everything else (including whitespace padding, `1`/`0`, `yes`/`no`, empty) raises `CLIError`. Scaffolds the shared `--meta` / `--ids` `true|false` parser for items 5 and 6.
  - `parse_meta_json(raw: str) -> dict` — JSON-parses the value, then enforces "must be a JSON object" with two distinct error messages (`"--meta must be valid JSON: ..."` vs `"--meta must be a JSON object, got <type>"`) so callers can grep either failure mode.
- **`swc_workload/io.py::_validate_shape`** — added an optional `meta` check inside `walk()` (after required-fields loop, before recursing children): when `meta` is present on a node it must be a `dict`, else fail with `"'meta' must be an object" at <path>.meta`. Absent `meta` continues to load — preserves REQ-05 for legacy artefacts.
- **`swc_workload/commands/add_command.py`** — `AddCommand` updated:
  - New optional flag `--meta <json>` (`default=None`) on `add_arguments`.
  - Parsed up front via `parse_meta_json` (before any disk access) so error paths never touch `workload.json`.
  - New nodes always built with `"meta": meta` — default `{}` when the flag is omitted.
  - `add --json` shape unchanged — still `{id, title, status}` (per solution.md; `meta` echo lands in item 5).
- **No changes to `rename` / `delete` / `move` / `start` / `complete` / `reset`** — `meta` rides along through existing dict-in-place mutations. Sub-item 3.5 is a pin, not new code.

### Testing

- **TDD per sub-item.** Wrote failing tests first for each scenario, then implemented to green:
  - 3.1: `tests/unit/test_meta.py` — 26 tests covering the `parse_bool_flag` accept/reject sets and `parse_meta_json` happy + malformed + non-object paths (REQ-08, REQ-09).
  - 3.2 / 3.3 / 3.4 / 3.5: `tests/e2e/test_swc-workload_meta.py` — 24 subprocess-driven tests covering default `meta: {}` at every placement, the legacy-sibling REQ-07 case, three reads (`list`, `find`, `summary`, `list --json`) against a legacy fixture (no `meta` on items) with byte-for-byte snapshot equality post-read, every `--meta` error branch (malformed JSON + array/string/number/boolean/null) asserting no write occurred, and `rename` / `delete` (sibling preservation) / `move to` / `move <direction>` / `start` / `complete` / `reset` preserving a non-trivial `meta` byte-for-byte.
  - REQ-10 schema pin: `tests/unit/test_validate_shape_meta.py` — 8 tests, covers accept-no-meta, accept-empty, accept-nested, and rejects non-object variants (string, list, int, bool, None) with `meta` + `object` in the error message.
- **Manual verification:** ran `uv run python -m swc_workload add --help` and confirmed `--meta <json>` appears in the options block with the documented help text.

### Test results

- 159 tests passing, 0 failures (`uv run pytest`).
- Sub-suite counts: unit 39 (was 5 → +26 meta, +8 validate_shape_meta), e2e 120 (was 96 → +24 meta).
- Pre-existing regression pin `test_add_json_emits_id_title_status` still green — the `add --json` shape did not change.

### Pipeline

Per `.swc/feature_metadata/pipeline.md`:

- **Build (`uv run pytest tests/`):** exit 0, 159 passed in ~18s.
- **Dev environment:** not applicable (`swc-workload` is a console script — no long-running dev server). Skipped per pipeline.md.
- **Acceptance criteria:**
  - Full test suite (unit + e2e) green via `uv run pytest tests/` — confirmed.
  - `swc-workload --version` reports `1.2.0` — confirmed via `uv run python -m swc_workload --version`.

### Build confidence

High. Every requirement in `requirements.md` (REQ-01 through REQ-10) has at least one named scenario backing it, every error path is pinned non-zero with an on-disk no-write assertion, and the pre-existing 1.1.x behaviour pins (`test_add_json_emits_id_title_status`, the validator-rejects-malformed pins, the `--no-ids` text pin) are all still green. The implementation is small (one new module, two file edits) and matches the agreed solution.md verbatim.

### Scope flags

None.

### Approach needs revisiting

No.
