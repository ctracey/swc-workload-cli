# Solution Design — 4: New subcommands — get, update-meta, find-by-meta

## Approach

Build out `meta.py` with three more stateless helpers, then add three new command classes, registering them in `commands/__init__.ALL`. No changes to existing commands.

1. **`swc_workload/meta.py` gains:**
   - `parse_path(raw: str) -> tuple[str, ...]` — `""` → `()`; otherwise split on `.`. No validation beyond that (`:` and other non-`.` chars are legal segment characters per spec).
   - `read_at_path(meta: dict, path: tuple[str, ...]) -> tuple[bool, Any]` — walks `meta` dict-by-dict. Returns `(False, None)` on missing intermediate or missing key or non-object intermediate. Returns `(True, value)` otherwise — including when value is falsy (`None`, `0`, `False`, `""`).
   - `write_at_path(meta: dict, path: tuple[str, ...], value: Any) -> None` — mutates `meta` in place. Creates missing intermediates as `{}`. Raises `CLIError("--meta path '<partial>' traversed a non-object value at '<segment>'")` when an intermediate exists and is not a dict. Raises `CLIError` on empty `path` (callers must handle empty path before calling).
   - `parse_meta_value(raw: str) -> Any` — `json.loads` with a `CLIError` wrap for parse failure. Used by `update-meta` for non-empty paths (any JSON type accepted). Empty path keeps using the existing `parse_meta_json` (object required).

2. **`swc_workload/commands/get_command.py` — `GetCommand`:**
   - Positional `ref`. Optional `--meta true|false` (default `true`).
   - Resolves via existing `find_by_ref`; errors `CLIError(f"item {ref} not found")` on miss.
   - JSON output: single object (NOT wrapped in `{items: [...]}`); built on top of `render_item_json` plus a `meta` field whose value is `item.get("meta", {})` (REQ-15 projection); omitted when `--meta false`.
   - Text output: uses `render_item_text` with `show_ids=True`.

3. **`swc_workload/commands/update_meta_command.py` — `UpdateMetaCommand`:**
   - Positionals `ref`, `path`, `value`. No `--meta` flag (it operates on meta unconditionally).
   - `path == ""` branch: parse `value` via `parse_meta_json` (object required); set `item["meta"] = parsed`. Fully replaces existing meta.
   - `path != ""` branch: `parsed = parse_meta_value(value)`; `meta = item.setdefault("meta", {})`; `write_at_path(meta, parse_path(path), parsed)`.
   - Save and emit. JSON output: `{"id": <id>, "path": <path>, "value": <parsed>}`.

4. **`swc_workload/commands/find_by_meta_command.py` — `FindByMetaCommand`:**
   - Positional `path`. Optional positional `pattern` (`nargs="?"`). Optional `--meta true|false` (default `false`).
   - Presence branch (no pattern): iterate `iter_items(items)`; for each item, skip if `"meta" not in item` (legacy → no match, REQ-15); call `read_at_path(item["meta"], parse_path(path))`; keep when `found=True`.
   - Pattern branch: compile `re.compile(pattern)` once up front — wrap `re.error` as `CLIError(f"--pattern is not a valid regex: {e}")`. Then iterate as above; additional filter: `isinstance(value, str) and compiled.search(value)`.
   - JSON output shape mirrors `FindCommand`: `{matches: [...]}`. Each match is `{id, number, title, status}`; when `--meta true`, include `meta` (from on-disk `item.get("meta", {})`).
   - Text output mirrors `find`: `sym N (id) title` per line; "no matches" line when empty.

5. **`commands/__init__.ALL`** — append `GetCommand()`, `UpdateMetaCommand()`, `FindByMetaCommand()` after the existing transitions, preserving the existing init-first ordering convention.

## Test approach

Full TDD per sub-item, in this order. Each sub-item closes by marking done via `mcp__swc-workload__complete`:

- **4.1 — `tests/unit/test_meta_path.py`** — drive `parse_path`, `read_at_path`, `write_at_path`, `parse_meta_value` directly. Cover every row in REQ-16's example tables plus the failure modes. Implementation goes into `meta.py` to make tests green.
- **4.2 — `tests/e2e/test_swc-workload_get.py`** — REQ-01, REQ-02, REQ-03, REQ-15 (`get` half), REQ-17. Subprocess fixtures; assert via `json.loads(stdout)` and on-disk `workload.json` no-write where applicable.
- **4.3 — `tests/e2e/test_swc-workload_update_meta.py`** — REQ-04 through REQ-09, REQ-15 (update-meta half), REQ-17. Each error scenario asserts `workload.json` byte-for-byte unchanged.
- **4.4 — `tests/e2e/test_swc-workload_find_by_meta_presence.py`** — REQ-10, REQ-13 (default + `--meta true`), REQ-15 (find-by-meta half), REQ-17 (presence shape).
- **4.5 — `tests/e2e/test_swc-workload_find_by_meta_pattern.py`** — REQ-11, REQ-12, REQ-14, REQ-17 (pattern shape).

Each sub-item: failing test → minimum implementation to green → `uv run pytest` to confirm no regressions → mark sub-item done via MCP → next.

## Technical decisions

- **Legacy items in `find-by-meta` are silently skipped, even at empty path.** Rationale: aligns with the "no migration" principle. An item without `meta` has nothing to find. Once a write touches the item (via `update-meta`), it gets a `meta` field and becomes findable. Pinned in REQ-15.
- **Legacy items in `get` project `meta: {}` at read time.** Rationale: the JSON shape contract for `get` always includes `meta` (when `--meta true`), so legacy items need *something* — `{}` is the canonical empty. On-disk file is NOT rewritten. Pinned in REQ-15.
- **`read_at_path` treats a non-object intermediate as missing (returns `(False, None)`).** Rationale: this keeps `find-by-meta` predictable — a typo'd write that left `meta.a` as a string doesn't accidentally make `find-by-meta a.b` match. Pin via journey.
- **`write_at_path` raises `CLIError` on a non-object intermediate.** Asymmetric with read on purpose: writes are intentional, so silently creating below a string would clobber co-resident data. REQ-07.
- **Empty path is invalid for `write_at_path`** — `update-meta` handles the empty-path case directly (replace the whole `meta`). Pin via journey.
- **Pattern compilation happens once, up front.** Before any iteration, before any disk load is touched for matching. If the regex is invalid, fail fast — no partial output. REQ-14.
- **`update-meta` does not gain a `--meta` flag.** It is unconditional. The two `--meta` flags in this work item belong to `get` and `find-by-meta`.
- **JSON output shapes:**
  - `get --json`: single object `{id, number, title, status, children, [meta]}`. NOT wrapped.
  - `update-meta --json`: `{id, path, value}` where `value` is the parsed JSON value written (verbatim).
  - `find-by-meta --json`: `{matches: [{id, number, title, status, [meta]}]}`. Mirrors `find`.
- **`find-by-meta` is added to the read-command cluster in `ALL`.** Order: `... SummaryCommand(), GetCommand(), FindByMetaCommand(), AddCommand(), ... UpdateMetaCommand()` — putting `get` + `find-by-meta` next to `find`/`summary`, and `update-meta` next to the existing write commands. This is a registration-order tweak only; argparse renders subcommands alphabetically in help text.

## Deferred

- **`--meta` / `--ids` on `list` / `find` / `summary` and `--no-ids` removal** — item 5.
- **`--meta <json>` on `start` / `complete` / `reset`** — item 6 (will reuse `parse_meta_json` + `parse_path` + `write_at_path` to apply the multi-path object atomically).
- **Docs and README** — item 7.
- **`add --json` emitting `meta`** — folded into item 5's read-default work; out of scope here.

## Notes

- Reuse `find_by_ref` from `tree.py` for ref resolution in both `get` and `update-meta`. Same error message pattern as `rename` / `delete` / `move`.
- `update-meta` MUST go through `load_workload_from_args` + `save_workload` (not raw `Path.write_text`) — that keeps the validate-on-load path active, so a workload with an item whose `meta` is non-object (somehow) would surface at load, not at write.
- After implementing 4.2, run the existing `find` e2e suite to confirm no regression — `find` and `find-by-meta` are sibling commands sharing the `{matches:[...]}` output shape, but they are separate code paths.
- `parse_meta_value` is its own helper (not `parse_meta_json` with a flag) so callers stay readable: `update-meta` uses one for empty path and the other for non-empty path; the call site itself tells you which branch you're in.
- After all sub-items pass, run `uv run python -m swc_workload get --help`, `update-meta --help`, `find-by-meta --help` to spot-check the help text reads naturally.
