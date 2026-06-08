# swc-workload CLI Tool

![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/github/v/tag/ctracey/swc-workload-cli?filter=v*&label=version)

A pip-installable CLI — a path-driven tree manager for `workload.json` files.

This is the binary half of [Sessionless Workload Context (SWC)](https://github.com/ctracey/swc),
extracted so other tools can depend on it without pulling in the full
SWC skills suite.

Designed to work with [swc-workload MCP Server](https://github.com/ctracey/swc-workload-mcp/tree/docs/mcp-client-registration)

## What it does

`swc-workload` manages a hierarchical workload tree persisted as
`workload.json`. It is purely a tree manager: it knows nothing about git
branches, context resolution, or `.swc/_meta.json`. Every operation
takes `--workload <folder>` and operates on `<folder>/workload.json`.

```
swc-workload <op> --workload <folder> [args]
```

Run `swc-workload --help` for the full subcommand list, or
`swc-workload <op> --help` for detailed usage and examples for any command.

## Commands

| Command | What it does |
|---------|-------------|
| `init` | Initialise a workload folder |
| `exists` | Check whether a workload exists (exit 0/1) |
| `list` | Render the tree; filter/exclude by status; scope to a subtree ref |
| `find` | Search by title substring, or by meta path (presence + regex) |
| `summary` | Count items by status |
| `get` | Fetch a single item as JSON |
| `add` | Add a new item (append or insert at position) |
| `update` | Update title, status, or a meta path on an item |
| `delete` | Remove an item and its children |
| `move` | Re-order or re-parent an item |

All commands accept `--json` for structured output. Run `swc-workload <cmd> --help` to see the full argument list and examples.

## Meta field

Every item carries a `meta` field — a free-form JSON object for caller-owned data.
New items default to `meta: {}`. Legacy items without a `meta` field are read
without error and gain the field on their first write.

**Reading meta:** `get` and all `--json` outputs always include the full `meta` blob.
`find --meta <path>` searches across items by meta content (presence or regex pattern).

**Writing meta:**
```
swc-workload update <ref> meta.<path> <value>  --workload <folder>
swc-workload update <ref> meta        <json>   --workload <folder>  # replace root
```

Values are parsed as JSON first; plain text falls back to a string, so `update 1 meta.stage plan` works without shell quoting. See `swc-workload update --help` for full examples including array index writes (`meta.tags[0]`).

**Caller convention:** use `vendor:purpose` as the top-level namespace for meta keys to avoid collisions between tools. The `:` character is a literal segment separator — do not use `.` in namespace names since `.` is the path separator for `find --meta` and `update meta.*`.

```
# Good — colon-namespaced
update 1 meta.swc:status.stage plan

# Avoid — dot in namespace clashes with path traversal
update 1 meta.swc.status.stage plan   # reads as path swc → status → stage
```

## Breaking changes from 1.1.x

The 1.2.0 release consolidates several commands. Callers should migrate:

| Old command | 1.2.0 equivalent |
|-------------|-----------------|
| `rename <ref> <title>` | `update <ref> title <title>` |
| `start <ref>` | `update <ref> status in-progress` |
| `complete <ref>` | `update <ref> status done` |
| `reset <ref>` | `update <ref> status not-started` |
| `update-meta <ref> <path> <value>` | `update <ref> meta.<path> <value>` |
| `update-meta <ref> "" <json>` | `update <ref> meta <json>` |
| `find-by-meta <path> [pattern]` | `find --meta <path> [pattern]` |

Status aliases (`todo`, `wip`, `complete`) are accepted by `update status`.

## Installation

Install directly from git with [pipx](https://pipx.pypa.io/) (recommended)
or [uv](https://github.com/astral-sh/uv); both put the `swc-workload`
command on your PATH in an isolated venv:

```
pipx install git+https://github.com/ctracey/swc-workload-cli.git

# or:
uv tool install git+https://github.com/ctracey/swc-workload-cli.git
```

Pin a version with `@<tag>` or `@<commit>`. Plain `pip install
git+...` works too (use a venv to avoid polluting your system Python).

## Upgrading

To get the latest version of the cli tool from the originally-installed git ref:

```
pipx upgrade swc-workload

# or:
uv tool upgrade swc-workload
```

To move to a specific tag (or switch refs), reinstall with `--force`:

```
pipx install --force git+https://github.com/ctracey/swc-workload-cli.git@v1.1.3

# or:
uv tool install --force git+https://github.com/ctracey/swc-workload-cli.git@v1.1.3
```

Check the installed version with `swc-workload --version`.

## Versioning

`swc-workload` follows [Semantic Versioning](https://semver.org/):
`MAJOR.MINOR.PATCH`.

- **MAJOR** — incompatible changes to CLI surface or `workload.json`
  on-disk format.
- **MINOR** — backwards-compatible new subcommands, flags, or
  behaviors.
- **PATCH** — backwards-compatible bug fixes and documentation-only
  updates.

The canonical version lives in `swc_workload/_version.py` and is
exposed via `swc-workload --version`. Each release is tagged in git
as `v<MAJOR>.<MINOR>.<PATCH>` (e.g. `v1.1.0`); pin an install with
`pipx install git+...@v1.1.0`.

Releases are cut by manually triggering the `Release` workflow — it
does not run automatically on push. Either use the **Run workflow**
button on the [Actions tab](../../actions/workflows/release.yml), or
the CLI:

```
gh workflow run release.yml -f bump=patch   # or: minor, major
```

The workflow bumps `_version.py`, commits, tags `v<new>`, pushes, and
publishes a GitHub Release.

## Tests

The repo pins its Python version in `.python-version` (also what CI
uses). [uv](https://github.com/astral-sh/uv) reads that file, installs
the interpreter if missing, creates the venv, and installs the package
in one short flow:

```
uv venv                          # reads .python-version, installs the interpreter if needed
uv pip install -e . pytest       # installs into .venv
```

The venv isolates this install from any global or pipx-installed
`swc-workload`, so the suite reliably exercises the local source.

Then run the suite via `uv run`, which always uses the project's
`.venv` regardless of shell activation or `pytest` shims on PATH:

```
uv run pytest tests/            # full suite
uv run pytest tests/unit/       # unit only
uv run pytest tests/e2e/        # end-to-end (subprocess) only
```

The e2e tests under `tests/e2e/` invoke `python -m swc_workload` via
`sys.executable`, so they always run against the Python (and editable
install) of the project venv — never a `swc-workload` binary that
happens to be on PATH. The entry-point smoke test in
`tests/unit/test_entry_point.py` verifies that `pip install -e .`
registered the `swc-workload` console script; it fails with a clear
"run `pip install -e .`" message if you skip the install step.

No git, network, or other external state required.
