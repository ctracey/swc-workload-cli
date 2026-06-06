# Implementation Context — Work Item 4

## Pass 1 — 2026-06-04

### 4.1 — meta.py dotted-path helpers
- **Decision:** `parse_path("a..b")` → `("a", "", "b")` (preserve adjacent empty segments verbatim). Per solution.md "No validation beyond that". Avoids over-validating something the spec deliberately leaves opaque.
- **Decision:** `read_at_path` returns the `meta` dict by reference for the empty-path case (not a copy). Safe because all read sites are emitting JSON downstream and not mutating the returned value; matches `(True, value)` shape with `value = meta`.
- **Decision:** `write_at_path` error message format — `cannot traverse non-object value at meta path '<traversed>' (existing value is <type>)`. Mentions the path so REQ-07's "stderr mentions the path" gherkin passes naturally.
- **Decision:** `parse_meta_value` error wraps with `<value> is not valid JSON: <msg>` so the `--meta <json>` error from `parse_meta_json` ("--meta must be valid JSON") and the `<json-value>` error from `update-meta` remain distinguishable in stderr greps.
- 42 new unit tests in `tests/unit/test_meta_path.py`; full suite 201 passing.

### 4.2 — GetCommand
- **Decision:** `GetCommand` reuses `render_item_json` for the body and appends `meta` (defaulting to `{}` for legacy items) as a top-level key. Keeps the renderer pure and `get`'s shape contract sits in the command rather than baking a `meta` projection into the shared renderer (which would also affect `list` later).
- **Decision:** `--meta` value parser is the existing `parse_bool_flag`. Defaults at the argparse layer (`default="true"`), parsed inside `execute()` so the failure path mirrors `--ids` later (REQ-13).
- **Decision:** Registered between `SummaryCommand` and `AddCommand` per solution.md (read cluster).
- **Decision:** Text output uses `render_item_text(item, number, show_ids=True)`, mirroring `list <ref>` behaviour.
- 15 new e2e tests in `tests/e2e/test_swc-workload_get.py`; full suite 216 passing.

### 4.3 — UpdateMetaCommand
- **Decision:** Value is parsed up front (before `load_workload_from_args`) so malformed JSON / non-object root never reaches the file write — keeps the no-write-on-error guarantee centralised.
- **Decision:** Text output: `[<id>] meta <path> updated` (e.g. `[a1b2c3d] meta swc:status.stage updated`). Empty path renders as `<root>` for readability. JSON output shape: `{id, path, value}` — `path` is the raw input string (preserves empty string).
- **Decision:** Registered as the LAST item in `ALL` (after `CompleteCommand`). Solution.md suggested "next to the existing write commands" — slotting it at the end of the write cluster keeps the diff to `__init__.py` minimal and mirrors `add` / `rename` / `delete` placement.
- **Decision:** On legacy items (`meta` field absent), `setdefault("meta", {})` creates `meta` on the in-memory dict before `write_at_path` runs — that captures REQ-15's "MAY add the meta key (since it is a write)" path.
- 30 new e2e tests in `tests/e2e/test_swc-workload_update_meta.py`; full suite 246 passing.

### 4.4 — FindByMetaCommand (presence mode)
- **Decision:** Single command class covers both presence + pattern modes (pattern arg is `nargs="?"`). The pattern branch is implemented now (4.5 just adds the test file) — keeping it together in 4.4 avoids a partial command that would surprise a code reader.
- **Decision:** Legacy items (no `meta` key) NEVER match, including empty path. Pinned per solution.md and REQ-15. Test `test_find_by_meta_empty_path_against_legacy_workload_returns_empty` exercises this.
- **Decision:** Match-entry shape: `{id, number, title, status}` (default) or `+ meta` (when `--meta true`). Mirrors `find` output exactly, with `meta` as the only addition.
- **Decision:** Text output is `no matches` (no quoted needle) when empty — there's no single needle for find-by-meta (path + optional pattern), so we use the simpler line. Mirrors `find`'s general approach.
- **Decision:** Registered between `GetCommand` and `AddCommand` per solution.md (read cluster, next to `find`/`summary`/`get`).
- 19 new e2e tests in `tests/e2e/test_swc-workload_find_by_meta_presence.py`; full suite 265 passing.

### 4.5 — FindByMetaCommand pattern mode
- **Decision:** Pattern compilation happens up front (before `load_workload_from_args`) so an invalid regex fails fast with no disk I/O. REQ-14.
- **Decision:** Non-string leaves are silently dropped in pattern mode — `not isinstance(value, str)` check after `read_at_path` confirms `found=True`. REQ-12.
- **Decision:** Implementation already shipped in 4.4 (single command class handles both modes). 4.5 just adds the focused pattern-mode test file — splits the spec sub-items along the test boundary that solution.md called out.
- 13 new e2e tests in `tests/e2e/test_swc-workload_find_by_meta_pattern.py`; full suite 278 passing.

### Wrap-up
- Help text spot-checked for `get`, `update-meta`, `find-by-meta` — reads naturally per solution.md instruction.
- Parent work item 4 auto-rolled to `done` once all five sub-items completed.

## Pass 2 — 2026-06-06

### F-01 — `update-meta` empty-path error messages name the wrong flag
- **Decision:** Took option (b) from the review note — split `parse_meta_json` into a flag-agnostic core `parse_meta_object(raw, *, label)` and kept `parse_meta_json` as a thin wrapper that pins `label="--meta"`. This preserves the verbatim error wording the `add --meta` callers (and the MCP integration tests that grep for it) expect, while letting the `update-meta` empty-path branch surface `<json-value>` instead. Option (a) — catch-and-re-raise inside `UpdateMetaCommand` — was rejected: it would leave the wrong label flowing through `parse_meta_object`'s call frame and double the surface area for item 6 to thread the right label.
- **Decision:** `parse_meta_object` is the new public name (not `_parse_json_object`) — the leading underscore would mark it as private and item 6 will reuse it through the same import path for `start`/`complete`/`reset` `--meta <json>` parsing. Keeping it public-by-name advertises the intended reuse.
- **Decision:** `label` is keyword-only (`*, label`). The label is meaningful but easy to forget at a call site; keyword-only forces every caller to spell it out and prevents a future `parse_meta_object("...", "")` typo.
- **Decision:** Added one e2e test per failure mode (`non-object` and `malformed JSON`) that asserts `<json-value>` appears AND `--meta` does NOT — pins the corrected wording on both branches simultaneously. The pre-existing `assert "object" in result.stderr.lower()` / `assert "json" in result.stderr.lower()` checks remain (they happen to still pass with the new wording), so the loose substring contract is also preserved.
- **Decision:** Did NOT touch the existing `assert "object" in stderr.lower()` / `assert "json" in stderr.lower()` checks. The review note observed that the e2e tests pass because they grep for those substrings — those substrings are still present in the corrected message, so deleting the loose checks would lose coverage of the existing failure-mode shape. The new tests layer a stricter label check on top.
- 3 new unit tests in `tests/unit/test_meta.py` (label-aware core + `parse_meta_json` label preservation), 2 new e2e tests in `tests/e2e/test_swc-workload_update_meta.py` (empty-path stderr label).
- Full suite: 278 → **283 passing, 0 failed** via `uv run pytest tests/`.
- Smoke-tested via the installed `swc-workload` CLI: `update-meta 1 "" '"a string"'` → `<json-value> must be a JSON object, got string`; `add "x" --meta '"oops"'` → `--meta must be a JSON object, got string`. Labels routed correctly.
