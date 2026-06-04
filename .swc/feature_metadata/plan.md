# Plan

## Goal / Why

Add per-workitem `meta` support to the `swc-workload` CLI as a breaking change (version `1.2.0`).

The CLI is the upstream contract for the `swc-workload-mcp` (a thin subprocess wrapper). Every meta-attributes capability the MCP wants to expose — opaque JSON tree per item, dotted-path reads/writes, atomic meta writes on status transitions, presence/regex search — must exist in the CLI first. Without these primitives the MCP cannot ship its meta-attributes feature or its integration/e2e tier.

Success looks like:
- CLI exposes new subcommands (`get`, `update-meta`, `find-by-meta`) and `--meta` flags on existing read/transition commands, all matching the contract in `cli-change-spec.md`.
- `--version` emits `1.2.0`.
- Pre-existing artefacts without `meta` load cleanly (no migration step).
- MCP test harness can pin against these contracts.

## Users and scenarios

- **Primary:** `swc-workload-mcp` — consumes every new capability and depends on exact shape adherence.
- **Secondary:** direct CLI users — affected by one breaking change (`--no-ids` removed in favour of `--ids false`) and the new optional flags.

## Background

The contract for this work lives at the repo root in `cli-change-spec.md`. That document is the authoritative reference for shapes, flags, semantics, and out-of-scope items.

## Approach

Two phases:

1. **Refactor** — restructure the existing `cli.py` (1138 lines, single file) into a cleaner module layout before any meta-feature work begins. Target shape is TBD (revisit in delivery / breakdown).
2. **Metadata feature** — strict TDD per subcommand on the refactored surface. New module `swc_workload/meta.py` holds dotted-path helpers; `cli.py` (or its successor) keeps the subcommand wiring and imports the helpers.

See `architecture.md` for full design.

## Features

- `--version` flag emits `1.2.0`.
- New `meta: {}` field on every workitem (default; opaque JSON tree).
- New subcommand `get <ref> [--meta true|false]` (meta default `true`).
- New subcommand `update-meta <ref> <path> <json-value>` with replace-not-merge semantics; empty path replaces the whole `meta`.
- New subcommand `find-by-meta <path> [<pattern>] [--meta true|false]` with presence + path-and-regex modes.
- `add` gains `--meta <json>`.
- `list` gains `--meta` and `--ids` (both `true|false`); `--no-ids` removed.
- `find` / `summary` gain `--meta true|false`.
- `start` / `complete` / `reset` gain `--meta <json>` for atomic status+meta writes.
- Reads tolerate pre-existing artefacts without `meta`; no migration.

## Delivery shape

1. **Refactor first** — restructure `cli.py` before any feature work. Target module shape decided in breakdown.
2. **Version + `--version`** — bump `_version.py` to `1.2.0` and surface via `--version`. MCP gates on this.
3. **`meta` field foundation** — default `meta: {}` on new items; reads tolerate pre-existing items without `meta`; `add --meta <json>` writes the field.
4. **New subcommands** — `get`, `update-meta`, `find-by-meta` against the foundation.
5. **Changed reads** — `--meta true|false` on `list` / `find` / `summary`; `--ids true|false` on `list` (removes `--no-ids`).
6. **Atomic transitions** — `--meta <json>` on `start` / `complete` / `reset`.

## Out of scope

(firm — per spec)

- Data migration of pre-existing workloads.
- Query language richer than dotted-path + regex on string values.
- Meta-derived synthesis in `summary` (counts stay status-only).
- Hard size cap on `meta`.
- First-class `notes` field.
- Separate `set-meta` / `patch-meta` tools.
- Bulk-add.

## Open Questions

(none — see `notes.md`)

