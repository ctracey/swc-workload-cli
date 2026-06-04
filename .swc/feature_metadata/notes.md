# Notes

## Decisions

- Target version: `1.2.0` (breaking).
- **Refactor before feature work**: restructure `cli.py` (currently 1138 lines, single file) before any metadata changes land. Target shape: helper modules (`errors`, `io`, `tree`, `status`, `validation`, `output`, `filters`) + `commands/` package with one file per command class. See `architecture.md` for the full layout and class pattern.
- **Incremental refactor**: extract shared modules first (phase A), introduce `Command` base + dispatch (phase B), then migrate one tool at a time with tests green between each step (phase C). Status-transition commands (`reset`/`start`/`complete`) are independent sibling classes (no inheritance), all delegating to `status.set_status(...)`.
- Strict TDD — failing e2e test from the spec's "Test recommendations" before any subcommand implementation.
- New module `swc_workload/meta.py` houses dotted-path parse/read/write and leaf-replace helpers; `cli.py` (or its successor) imports them.
- No deferrals — spec's out-of-scope list is firm.
- `--meta true|false` and `--ids true|false` use a shared bool parser, consistent across all subcommands.
- Atomicity of status-transition `--meta` writes falls out of the existing whole-file write — meta updates happen in memory before the single artefact write.
- Path-segment invariant: `:` is a literal character; only `.` separates segments. Callers should avoid `.` in the namespace half of `vendor:purpose`.

## Solution decisions

(merged above — kept as one Decisions section for this work item.)

## Open questions

(none — spec is the contract.)

## Deferred decisions

(none — see Decisions.)

## Risks

- Existing JSON-output consumers may not tolerate the new `meta` key on `list` / `find` / `summary` / `get`. Spec calls this out as breaking-but-soft; surface in the release notes.
- `--no-ids` removal will break callers that still pass that switch. Hard break; doc clearly.

## References

- `cli-change-spec.md` (repo root) — authoritative contract for the change.

