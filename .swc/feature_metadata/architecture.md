# Architecture

## Context

The `swc-workload` CLI is a single-package Python project (`swc_workload/`) built with `hatchling`. The interactive surface is the `swc-workload` console script entry point, wired via `pyproject.toml` to `swc_workload.cli:main`. All subcommand parsing, dispatch, and workload mutation today live in one file: `swc_workload/cli.py` (~1138 lines). Reads and writes round-trip the entire `workload.json` per call.

## Tech stack

- Python ≥ 3.9
- Build: `hatchling` (version dynamic from `swc_workload/_version.py`)
- Dev / test: `uv` (`.python-version` pinned), `pytest`
- Tests in two tiers:
  - `tests/unit/` — direct module imports
  - `tests/e2e/` — subprocess invocation via `python -m swc_workload`
- No third-party runtime deps (stdlib only).

## Folder structure

Target tree after the refactor (item 1) and meta work (items 2–7):

```
swc_workload/
  __init__.py
  __main__.py
  _version.py        # canonical version string (bump to 1.2.0)
  cli.py             # slim: main(), parser bootstrap, dispatch over ALL commands
  errors.py          # CLIError
  io.py              # load/save/validate workload.json + friendly OSError wrap
  tree.py            # make_id, all_ids, iter_items, find_by_ref, sibling-collision
  status.py          # derive_parent_status, rollup, _rollup_ancestors, set_status
  validation.py      # validate_title, ref/dotted-number/hash validators
  output.py          # render_text, to_json_tree (text + JSON renderers)
  filters.py         # parse_filter, apply_filters, normalise_status
  meta.py            # (1.2.0) dotted-path parse/read/write + leaf-replace
  commands/
    __init__.py            # ALL = [InitCommand(), ExistsCommand(), ...]
    command.py             # Command base class + add_common + run_status_transition
    init_command.py
    exists_command.py
    list_command.py
    find_command.py
    summary_command.py
    add_command.py
    rename_command.py
    delete_command.py
    reset_command.py
    start_command.py
    complete_command.py
    move_command.py
    # added during 1.2.0:
    get_command.py
    update_meta_command.py
    find_by_meta_command.py
tests/
  unit/
  e2e/
```

Filenames match the class they contain (`AddCommand` → `add_command.py`). No stdlib shadowing concerns at this length.

## Class pattern (commands/)

```python
class Command:
    name: str           # subcommand name, e.g. "add"
    help: str           # one-line help shown in argparse listing

    def register(self, subparsers) -> None:
        """Add this command's subparser (positionals + options) to argparse."""

    def execute(self, args) -> int:
        """Run the command. Return process exit code."""
```

- One file per command. Every subcommand is a class — including tiny ones like `init` and `exists`, for consistency.
- `commands/__init__.py` exposes an explicit `ALL = [...]` list. `cli.py:main()` iterates `ALL`, calls `register()` on each, then dispatches `execute()` on the matched subparser. No auto-discovery.
- `reset` / `start` / `complete` are three independent sibling classes (no shared base beyond `Command`); each calls `status.set_status(...)` from the `status` module. Flatter than an inheritance chain, easier to refactor incrementally.
- `Command` is intentionally minimal. No options spec abstraction — each command's `register()` calls argparse directly. The class is a packaging unit, not a framework.

## Design

- **Opaque tree** — the CLI never inspects the shape of `meta` beyond locating dotted-path keys. Validation is the caller's job. No schema, no per-namespace handlers.
- **Path syntax** — dotted segments only. No JSONPath, no array indexing. `""` (empty path) = root of `meta`. `:` is a literal character in a segment (so `swc:workflow-status` is one segment). Per the spec, callers should avoid `.` in the namespace half of `vendor:purpose`.
- **Reads tolerate absence** — missing intermediate path → "no value at path", not an error. Pre-existing artefacts without a `meta` field load cleanly.
- **Writes are replace-not-merge** — `update-meta` at any path replaces the value there fully, including objects (no shallow merge with co-resident keys).
- **Atomicity** — existing CLI semantics already write the whole `workload.json` in one operation, so the spec's "status flip + every meta write together" requirement falls out of the existing write path. The meta writes happen in-memory before the single artefact write.
- **`--meta true|false`** — parsed identically across `list`, `find`, `summary`, `add`'s output, `get`, etc. Shared helper.
- **`--ids true|false`** — replaces removed `--no-ids`. Identical bool parser.

## Decisions

- Strict TDD per subcommand: write failing e2e from the spec's "Test recommendations" section first, then implement.
- Meta helpers in their own module (`swc_workload/meta.py`), not inlined in `cli.py`.
- No deferrals — spec's out-of-scope items are firm "won't do".

## Constraints

- Existing parsers may include the new `meta` field, so MUST tolerate it appearing in `list` / `find` / `summary` / `get` JSON output. Spec calls this out as a caller-visible breaking note.
- `--no-ids` switch removed. Callers must migrate to `--ids false`. This is a breaking change versus 1.1.x.
- No data migration on read. Pre-existing items without `meta` stay that way until a write touches them.
- No hard cap on `meta` size in this version.

