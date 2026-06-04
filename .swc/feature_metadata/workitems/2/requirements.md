# Requirements — 2: Bump version to 1.2.0 and surface via --version

## Intent

Bump the `swc-workload` CLI version from `1.1.3` to `1.2.0` and confirm `swc-workload --version` reflects the new value as a **bare version string** (no prog-name prefix). The `--version` flag already exists in `cli.py`, but currently uses argparse's default `version=f"%(prog)s {__version__}"` format which emits `swc workload 1.1.3`. The cli-change-spec.md contract is explicit: "Output: a single version string (e.g. `0.4.0`) on stdout, exit 0. The MCP's new `version` tool shells out to read this." That requires a one-line change to the argparse format.

The bump is the **gating commit** for the upcoming meta-attributes work (`cli-change-spec.md`). The downstream `swc-workload-mcp` shells out to `swc-workload --version` to expose the CLI version and will pin against `>=1.2.0` for its meta-feature tests. Landing 2 ahead of items 3–7 lets the MCP start its work in parallel.

Per the project's semver policy (README §Versioning), the metadata changes are a MINOR bump — not MAJOR — because the `workload.json` on-disk shape stays backwards-compatible (new `meta` field is additive and opaque; reads tolerate items without it).

## Constraints

- `_version.py` is the canonical source. `pyproject.toml` (`tool.hatch.version.path = "swc_workload/_version.py"`) and `README.md §Versioning` both establish this.
- `--version` output must be the bare version string, nothing else. Per cli-change-spec.md, the MCP shells out and reads it directly.
- The pinning test must assert the **exact stripped output equals `"1.2.0"`** — not just substring containment. A substring assertion would also pass for `swc workload 1.2.0`, hiding a regression on the format change.
- Existing tests in `tests/e2e/test_swc-workload_help.py` use `__version__` and substring containment; they continue to pass either way (`__version__` is a substring of both old and new output). They don't pin the format and shouldn't be relied on for the format guarantee.
- This work item lands as its own commit, separate from feature work in items 3–7. The MCP needs a stable ref to pin.

## Out of scope

- None.

## Approach direction

Three small steps matching the sub-items:

- **2.1** Change `--version` argparse format in `cli.py:build_parser()` from `version=f"%(prog)s {__version__}"` to `version=f"{__version__}"` so the output is the bare version string. (Originally scoped as "verify wired" but the spec-aligned format change goes here.)
- **2.2** Edit `swc_workload/_version.py` from `__version__ = "1.1.3"` to `__version__ = "1.2.0"`.
- **2.3** Add one e2e test asserting `swc-workload --version` output, when stripped, equals exactly `"1.2.0"`.

Single small commit.

## Parked

- CHANGELOG / release notes for `1.2.0` are deliberately deferred to work item 7 (Docs + release notes), so they accumulate alongside the metadata feature work and land in one cohesive doc commit at the end.
