# swc-workload

![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/github/v/tag/ctracey/swc-workload-cli?filter=v*&label=version)

A pip-installable CLI — a path-driven tree manager for `workload.json` files.

This is the binary half of [Sessionless Workload Context (SWC)](https://github.com/ctracey/swc),
extracted so other tools can depend on it without pulling in the full
SWC skills suite.

## What it does

`swc-workload` manages a hierarchical workload tree persisted as
`workload.json`. It is purely a tree manager: it knows nothing about git
branches, context resolution, or `.swc/_meta.json`. Every operation
takes `--workload <folder>` and operates on `<folder>/workload.json`.

```
swc-workload <op> --workload <folder> [args]
```

Run `swc-workload --help` for the full subcommand list.

## Installation

Install directly from git with [pipx](https://pipx.pypa.io/), which puts
the `swc-workload` command on your PATH in an isolated venv:

```
pipx install git+https://github.com/ctracey/swc-workload-cli.git
```

Pin a version with `@<tag>` or `@<commit>`. Plain `pip install
git+...` works too (use a venv to avoid polluting your system Python).

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

## Tests

Create a virtualenv first, then install the package into it in editable
mode. The venv isolates this install from any global or pipx-installed
`swc-workload`, so the suite reliably exercises the local source:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then run the suite:

```
pytest tests/
```

The CLI tests invoke `python -m swc_workload` via `sys.executable`, so
they always run against the Python (and editable install) of the
active venv — never a `swc-workload` binary that happens to be on PATH.
The entry-point smoke test in `tests/test_entry_point.py` verifies
that `pip install -e .` registered the `swc-workload` console script;
it fails with a clear "run `pip install -e .`" message if you skip
the install step.

No git, network, or other external state required.
