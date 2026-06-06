# Requirements — 4: New subcommands — get, update-meta, find-by-meta

## Intent

Add three new top-level subcommands that operate on the `meta` field laid down in item 3, matching the contract in `cli-change-spec.md`:

- **`get <ref>`** — return a single item by ref (number or hash). JSON output is a single object, not an array. Errors on miss.
- **`update-meta <ref> <path> <json-value>`** — write a JSON value at a dotted `<path>` inside the item's `meta`. Replace-not-merge at the leaf; empty path replaces the whole `meta`; intermediate objects created as needed.
- **`find-by-meta <path> [<pattern>]`** — search for items by `meta` content. Presence mode (no pattern) matches any value at the path; pattern mode requires the leaf be a string AND the regex match. Missing path / non-string leaf in pattern mode → no match (silently, no error).

After this item, the `swc-workload-mcp` can wire its meta-attributes tools end-to-end against the CLI.

## Constraints

- **Spec is the contract.** Shapes, defaults, and error behaviours match `cli-change-spec.md` § "New CLI subcommands" exactly.
- **Path syntax is dotted only.** No JSONPath, no array indexing, no `[*]`. `:` is a literal character; only `.` separates segments. Empty path (`""`) refers to the root of `meta`.
- **Reads tolerate absence.** Missing intermediate paths return "no value" (or "no match" in find-by-meta); they are NOT errors.
- **Replace-not-merge at every depth.** `update-meta <ref> swc:status '{"stage":"review"}'` fully replaces whatever was at `swc:status` — no shallow merge.
- **Intermediate object creation.** `update-meta <ref> a.b.c '...'` creates `a` and `a.b` as objects if missing. If an intermediate exists but is not an object (e.g. a string or list), the command MUST error rather than silently overwrite — that protects the caller from typos that would clobber co-resident data.
- **`--meta` defaults differ per command:** `get` → `true`, `find-by-meta` → `false`. Matches the spec table.
- **Strict TDD per sub-item.** Failing test (unit for 4.1; e2e for 4.2–4.5) before implementation.

## Out of scope

- `--meta` / `--ids` flags on `list` / `find` / `summary` — those land in item 5. (`get` and `find-by-meta` get their own `--meta` flags here because they are new commands with bespoke defaults.)
- `--meta <json>` on `start` / `complete` / `reset` — item 6 (will reuse the `update-meta`-style writes built here).
- Bulk operations (`bulk-get`, `bulk-update-meta`). Not requested.
- A richer query language for `find-by-meta` (no comparison operators, no AND/OR composition, no array-element matching). Spec is firm.
- Adding `meta` to existing `list` / `find` / `summary` output shapes — item 5.

## Approach direction

Helpers go into `swc_workload/meta.py` (already exists). Each command is its own file in `swc_workload/commands/` and registered in `commands/__init__.ALL`:

1. **4.1 — `meta.py` extensions.** Three pure helpers:
   - `parse_path(raw: str) -> tuple[str, ...]` — splits on `.`; returns `()` for the empty-string root; rejects nothing else (no validation beyond emptiness rules — `:` and other punctuation are valid segment characters per the spec).
   - `read_at_path(meta: dict, path: tuple[str, ...]) -> tuple[bool, Any]` — returns `(found: bool, value)`. `found=False` for any missing intermediate or missing leaf; `found=True` even when the leaf value is `None` / falsy.
   - `write_at_path(meta: dict, path: tuple[str, ...], value: Any) -> None` — replaces in place; creates intermediate objects; errors via `CLIError` when an intermediate exists and is not an object. Empty path (`()`) is invalid here — the caller (`update-meta`) replaces the whole `meta` itself in that case.
2. **4.2 — `GetCommand`.** New file `get_command.py`. Resolves ref via existing `find_by_ref`; errors if not found. JSON output is the single object via `render_item_json` plus `meta` (default `true`, suppressible). Text output uses `render_item_text`.
3. **4.3 — `UpdateMetaCommand`.** New file `update_meta_command.py`. Positionals: `ref`, `path`, `json_value`. Empty path → replace whole `meta` with `parse_meta_json` (object required). Non-empty path → `parse_path` + `write_at_path` with the parsed JSON value (any JSON type accepted, not just objects). `update-meta --json` echoes `{id, path, value}` on success.
4. **4.4 — `FindByMetaCommand` presence mode.** New file `find_by_meta_command.py`. Single positional `path` plus optional `pattern`. Presence branch: walks all items, calls `read_at_path`, keeps items where `found=True`. Output shape mirrors `find` (`{matches: [...]}`).
5. **4.5 — `FindByMetaCommand` pattern mode.** Same command, when `pattern` is supplied: keep items where `found=True` AND leaf value is a `str` AND `re.search(pattern, leaf)` matches. Invalid regex → `CLIError` (user-friendly message). Missing path / non-string → no match (silent).

All three new commands gain `--meta true|false` via the shared `parse_bool_flag` already in `meta.py` — defaults per spec (`get` → `true`, `find-by-meta` → `false`). `--meta` is meaningful for the *output* shape (whether to include items' `meta` blobs); pattern matching itself always reads `meta`.

## Parked

- The exact stderr wording for "intermediate is not an object" is decided in solution.md (specs cover the failure mode itself, not the literal string).
- Whether `update-meta` should accept a `--json` flag is dispatched to convention: every existing command supports `--json` via `add_common`, so all three new commands inherit it. The structured output shapes are decided in solution.md.
- Item 5 will replace `find`'s default-text format too — `find-by-meta`'s text format should match what `find` lands in item 5 once read-flag work is in.  For 4.4/4.5 the text format mirrors the current `find` shape (`sym N (id) title`).
