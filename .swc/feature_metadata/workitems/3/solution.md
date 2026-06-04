# Solution Design — 3: meta field foundation — default {}, read tolerance, add --meta <json>

## Approach

Two pieces of code land before any subcommand behaviour changes:

1. **New module `swc_workload/meta.py`** — houses the two stateless helpers needed by this work item (`parse_bool_flag`, `parse_meta_json`) and reserves the namespace for the dotted-path helpers item 4 adds. No commands import it yet beyond `add`'s consumption of `parse_meta_json`.
2. **`io._validate_shape` gains an optional `meta` check** — if `meta` is present on a node, it MUST be a JSON object. Absent `meta` continues to load unchanged (legacy items keep working — REQ-05).

Then `AddCommand` is updated so:
- New nodes always carry `meta: {}` in the persisted shape (REQ-01).
- A new optional `--meta <json>` flag, parsed through `meta.parse_meta_json`, replaces that default when supplied (REQ-02–04).

Mutation commands (`rename`, `delete`, `move`, status transitions) require **no code change** for REQ-06 / REQ-07 because they all operate on dict objects in place — `meta` travels with the node naturally. Sub-item 3.5 is a defensive e2e pin only.

## Test approach

Full TDD per sub-item, in this order:

- **3.1** — unit tests in `tests/unit/test_meta.py` driving `parse_bool_flag` and `parse_meta_json` to satisfy REQ-08 / REQ-09. Module created to make tests pass.
- **3.2** — unit test pinning that the dict literal in `AddCommand.execute` ends up with `meta: {}` in the saved artefact; e2e via `swcw_ready` confirming `add` then reading `workload.json` from disk. Satisfies REQ-01 / REQ-07.
- **3.3** — e2e seeding `workload.json` directly (bypass `init`) with a legacy shape (no `meta` on items), running `list` / `find` / `summary`, and verifying (a) exit 0, (b) bytes-on-disk identical post-read. Satisfies REQ-05.
- **3.4** — e2e covering happy paths and every error case for `add --meta <json>`. Each error scenario asserts non-zero exit AND that `workload.json` contains zero items (no partial write). Satisfies REQ-02–04.
- **3.5** — e2e for each of `rename`, `delete`, `move` against an item with non-trivial `meta`, asserting `meta` survives byte-for-byte. Satisfies REQ-06.

Each sub-item: failing test → minimum implementation to green → run full suite (`uv run pytest`) → mark sub-item done via MCP `complete <N.M>` → next sub-item.

## Technical decisions

- **`parse_bool_flag` is strict.** Accepts the exact tokens `true` / `false` after `.casefold()` (case-insensitive). Rejects anything else — including padded whitespace, `1`/`0`, `yes`/`no`. Rationale: the architecture commits to a "shared bool parser" with a single spelling; lenient variants would force every caller to remember which were allowed.
- **`parse_meta_json` returns `dict`.** Signature: `parse_meta_json(raw: str) -> dict`. Raises `CLIError("--meta must be valid JSON: <parse error>")` on JSON failure and `CLIError("--meta must be a JSON object, got <type>")` on non-object. The two-error split makes failure modes greppable from the MCP test side.
- **`add --json` output unchanged for this work item.** Continues to emit `{id, title, status}` only — `meta` echo lands with the read-flag work in item 5. Tests for REQ-02 verify `meta` via the on-disk `workload.json` snapshot, not stdout.
- **Schema validator placement.** The optional-`meta` check goes inside `io._validate_shape.walk`, after the required-fields loop, as: `if "meta" in node and not isinstance(node["meta"], dict): fail("'meta' must be an object", f"{node_path}.meta")`. This is the existing validator's "fail at first violation, with JSON-path" pattern.
- **`empty_workload()` unchanged.** It still returns `{"items": []}` — `meta` is per-item, not per-workload-root.
- **Sub-item 3.5 has no implementation phase.** Tests confirm behaviour that already falls out of existing dict-passthrough semantics. If any test fails, that surfaces a real bug — investigate before changing tests.
- **Test fixture path.** Sub-item 3.3 uses the existing `swcw` fixture (not `swcw_ready`) so it can write the legacy shape to disk before any CLI invocation.

## Deferred

- **Read-side `meta` rendering** in `list` / `find` / `summary` / `get` JSON output — item 5 (default `false`) and item 4 (`get` default `true`).
- **Dotted-path helpers** in `meta.py` — item 4.1 adds `parse_path`, `read_at_path`, `write_at_path`, plus the leaf-replace semantics.
- **`--meta <json>` on status transitions** — item 6, using the same `parse_meta_json` helper added here.
- **Adding `meta` to the `add --json` output shape** — folded into item 5's read-default work.

## Notes

- `--meta` is registered on `AddCommand.add_arguments` with `default=None`. `None` means "use the empty object default"; a non-`None` string is fed straight to `parse_meta_json`. Keep the flag's help text aligned with the spec: `JSON object stored verbatim as the item's meta`.
- After 3.4, audit a single failing e2e against the existing pin `test_add_json_emits_id_title_status` (it expects `set(payload.keys()) >= {"id", "title", "status"}`). The current shape stays intact — `--json` does not emit `meta` yet — so this pin should remain green without change.
- Tests must read `workload.json` directly (via `json.loads(workload.read_text())`) to assert `meta` shape; do NOT rely on `list --json` output for `meta` assertions in this work item.
- Do not introduce a "migration" pass — REQ-05's bytes-identical guarantee depends on read commands never writing as a side effect.
