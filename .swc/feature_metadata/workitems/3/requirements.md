# Requirements — 3: meta field foundation — default {}, read tolerance, add --meta <json>

## Intent

Land the read-side foundation for per-workitem `meta` ahead of the new subcommands and changed reads (items 4–6). After this work item, every newly-created item carries `meta: {}` by default; legacy artefacts (without `meta` on any items) continue to load and operate without error; and `add` can write a verbatim JSON object into the new field via `--meta <json>`. The shared `--meta` / `--ids` `true|false` parser used across later phases is scaffolded here so it is one import away when items 4–6 begin.

This unblocks the `swc-workload-mcp` integration tier, which pins against the 1.2.0 CLI contract.

## Constraints

- **Spec is the contract** (`cli-change-spec.md`). Shapes and defaults must match exactly — MCP tests are written against them.
- **No migration.** Pre-existing artefacts without `meta` load unchanged. A field is only added when a write touches the item.
- **Opaque tree.** The CLI does not interpret `meta`. Validation of contents is the caller's job.
- **Strict TDD.** Each sub-item starts with a failing test (unit or e2e per the spec's "Test recommendations") before any implementation lands.
- **Preserve existing behaviour.** `rename`, `delete`, `move` must not drop or mutate an item's existing `meta`. Sub-item 3.5 pins this as a defensive test.
- **`--meta <json>` parsing.** The argument value is parsed as JSON; if it is not a valid JSON object, the command errors with a clear message and non-zero exit.

## Out of scope

- The new read flags (`--meta true|false` on `list` / `find` / `summary` / `get`) — those land in item 5.
- The new subcommands `get` / `update-meta` / `find-by-meta` — those land in item 4.
- `--meta <json>` on `start` / `complete` / `reset` — item 6.
- `--ids true|false` wiring on `list` (replacing `--no-ids`) — item 5. The bool parser is scaffolded here but no consumer is wired yet.
- Dotted-path read / write semantics in `meta.py` — item 4.1 adds the parser/resolver helpers.

## Approach direction

Two extraction modules, then `add` is wired through them:

1. **`swc_workload/meta.py`** — new module. Houses (a) a verbatim JSON-object parser for `--meta <json>` values (validate it parses and is an object; reject anything else with a CLI error), and (b) the shared `--meta` / `--ids` `true|false` bool parser used across phases 4–6. Dotted-path helpers come later in item 4 and live in this same module.
2. **Default `meta: {}` on item creation.** New nodes built by `AddCommand` (and any future creation paths) include `meta: {}`. `io._validate_shape` is left untouched — `meta` is optional on existing items by design.
3. **`add --meta <json>`.** Wire a new optional flag to `AddCommand`. When supplied, the parsed JSON object replaces the default `{}` verbatim. Sibling-collision and title validation rules are unchanged.
4. **Read tolerance.** Pre-existing items without `meta` continue to load and round-trip through `list` / etc. unchanged. Existing tests already cover the round-trip; the new pin is a fixture-based e2e against a `workload.json` that lacks `meta` on its items.
5. **Defensive preservation.** Existing `meta` on items is preserved through `rename` / `delete` / `move` operations — verify with a focused e2e covering each.

## Parked

- Sub-item 3.1's bool parser will be exercised in item 5 (read flags) and item 6 (transition flags). Tests in 3.1 cover the helper directly; integration with command surfaces is later.
- The recommended caller convention `vendor:purpose` (no `.` in namespace) is a docs guidance only — not enforced by `meta.py`. Docs update lands in item 7.
- Default JSON-output shape for `add` (currently `{id, title, status}`) does not yet surface `meta`. Whether `add --json` should echo `meta` falls under item 5's read-default work; for now `add` continues to emit the current shape.
