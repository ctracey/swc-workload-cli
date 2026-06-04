# Specs — 3: meta field foundation — default {}, read tolerance, add --meta <json>

## Users and Personas

- **`swc-workload-mcp` (primary)** — calls the CLI as a subprocess. Pins integration tests against exact JSON shapes from `cli-change-spec.md`. Goal: round-trip opaque `meta` through `add` and read it back through later subcommands without surprises. Precondition: invokes `swc-workload` with `--workload <folder>` and parses stdout JSON.
- **Direct CLI user (secondary)** — human running `swc-workload add ... --meta '{...}'` against a workload they own. Goal: stash structured-but-opaque per-item metadata. Precondition: the workload exists.
- **Legacy-artefact caller** — a caller (human or MCP) operating against a `workload.json` that pre-dates 1.2.0; existing items have no `meta` field. Goal: continue reading and mutating the artefact without an explicit migration. Precondition: items in the file lack `meta`.

## User Journeys

### Happy path — add a new item with default `meta: {}`
1. User runs `swc-workload add "title" --workload <folder>`.
2. CLI appends a new item with `meta: {}` already populated.
3. The on-disk `workload.json` shows `meta: {}` on the new item.

### Happy path — add a new item with `--meta <json>`
1. User runs `swc-workload add "title" --meta '{"swc:status":{"stage":"plan"}}' --workload <folder>`.
2. CLI parses the JSON, accepts it as the new item's `meta` verbatim, exits 0.
3. The on-disk `workload.json` shows the supplied object as the new item's `meta` (byte-for-byte equivalent JSON).

### Alternative path — `--meta` with deeply nested JSON object
1. User passes a multi-level nested object (mix of objects, arrays, strings, numbers, booleans, null).
2. CLI stores the value verbatim with no shape interpretation; round-trips intact.

### Non-happy path — read a legacy workload (`meta` absent on items)
1. Caller has a `workload.json` where every item is shape-valid but lacks `meta`.
2. Caller runs `swc-workload list --workload <folder>` (or any read).
3. CLI loads and renders successfully; no error, no implicit migration write to disk.

### Non-happy path — mutate a legacy workload without touching `meta`
1. Caller runs `swc-workload rename <ref> "new title"` against a legacy item (no `meta` field).
2. The renamed item is written; the saved item still lacks `meta` (it was not added by the mutation).
3. New items added in the same workload do receive `meta: {}` (they are created paths, not touched-existing paths).

### Defensive path — preserve existing `meta` through `rename`
1. Item exists with `meta: {"swc:status":{"stage":"plan"}}`.
2. Caller runs `rename <ref> "new title"`.
3. After save, the item has the new title and **the same** `meta` object byte-for-byte.

### Defensive path — preserve existing `meta` through `delete` (sibling preservation)
1. Items A, B, C exist; B has `meta` populated.
2. Caller runs `delete A`.
3. After save, B still has its `meta` byte-for-byte.

### Defensive path — preserve existing `meta` through `move`
1. Item exists at `2.3` with `meta` populated.
2. Caller runs `move 2.3 to 1.1`.
3. After save, the item is at its new position with the same `meta` byte-for-byte.

### Error path — `--meta` value is not valid JSON
1. Caller runs `swc-workload add "title" --meta '{not-json}' --workload <folder>`.
2. CLI exits non-zero; stderr describes a JSON parse error; no item is written.

### Error path — `--meta` value parses but is not a JSON object
1. Caller runs `swc-workload add "title" --meta '["a","b"]' --workload <folder>` (or `'"a"'`, `'42'`, `'null'`, `'true'`).
2. CLI exits non-zero; stderr indicates `--meta` must be a JSON object; no item is written.

### Internal path — shared `--meta` / `--ids` bool parser exists
1. The new `swc_workload/meta.py` module exposes a callable that converts the strings `"true"` / `"false"` (case-insensitive) to `True` / `False`, and raises a `CLIError` for any other value.
2. No command currently wires it (items 5 / 6 do). Unit tests cover the helper directly.

## Requirements

- **REQ-01** — WHEN a new work item is created via `add`, the CLI SHALL persist it with a `meta` field defaulting to an empty JSON object `{}`.
- **REQ-02** — WHEN `add` is invoked with `--meta <json>` where `<json>` is a valid JSON object, the CLI SHALL persist the new item with that object as its `meta`, verbatim (no shape interpretation, no key reordering required beyond standard JSON serialisation).
- **REQ-03** — IF `--meta <json>` is supplied to `add` and the value is not valid JSON, THEN the CLI SHALL exit non-zero with a stderr message identifying the parse failure and SHALL NOT modify `workload.json`.
- **REQ-04** — IF `--meta <json>` is supplied to `add` and the parsed value is not a JSON object (i.e. is an array, string, number, boolean, or `null`), THEN the CLI SHALL exit non-zero with a stderr message stating that `--meta` must be a JSON object and SHALL NOT modify `workload.json`.
- **REQ-05** — WHEN any read command (`list`, `find`, `summary`) is invoked against a workload whose items lack `meta`, the CLI SHALL load and render successfully and SHALL NOT rewrite `workload.json` as a side effect.
- **REQ-06** — WHEN any mutation command (`rename`, `delete`, `move`, status transitions) operates on an item that already has a `meta` field, the CLI SHALL preserve that item's `meta` exactly (same keys, same values, same nested structure).
- **REQ-07** — WHEN `add` is invoked without `--meta`, the resulting item's `meta` SHALL be `{}` regardless of whether sibling items in the workload have or lack a `meta` field.
- **REQ-08** — The `swc_workload.meta` module SHALL exist and SHALL expose a `parse_bool_flag(value: str) -> bool` helper that accepts `"true"` / `"false"` (case-insensitive) and raises `CLIError` for any other input.
- **REQ-09** — The `swc_workload.meta` module SHALL expose a `parse_meta_json(value: str) -> dict` helper that returns the parsed JSON object, raising `CLIError` on JSON parse failure or non-object types.
- **REQ-10** — IF a workload artefact contains an item with a `meta` field that is not a JSON object, THEN the existing schema validator SHALL reject the file with the existing invalid-shape error path. (Out of scope for change — but pinned so we don't accidentally weaken validation while adding the optional field on the write side.)

## Acceptance Scenarios

```gherkin
# REQ-01
Scenario: add without --meta creates an item with meta: {}
  Given an initialised workload
  When I run `add "first"` without --meta
  Then the command exits 0
  And the saved workload.json item has a "meta" field equal to {}
```

```gherkin
# REQ-02
Scenario: add --meta with a simple object stores it verbatim
  Given an initialised workload
  When I run `add "first" --meta '{"swc:status":{"stage":"plan"}}'`
  Then the command exits 0
  And the saved item's "meta" equals {"swc:status": {"stage": "plan"}}

# REQ-02
Scenario: add --meta with a nested object preserves shape verbatim
  Given an initialised workload
  When I run `add "first" --meta '{"a":{"b":[1,2,{"c":null}],"d":true}}'`
  Then the command exits 0
  And the saved item's "meta" equals {"a": {"b": [1, 2, {"c": null}], "d": true}}
```

```gherkin
# REQ-03
Scenario: add --meta with malformed JSON rejects without writing
  Given an initialised workload
  When I run `add "first" --meta '{not-json}'`
  Then the command exits non-zero
  And stderr mentions JSON or parse
  And workload.json contains zero items
```

```gherkin
# REQ-04
Scenario Outline: add --meta with a non-object JSON value rejects without writing
  Given an initialised workload
  When I run `add "first" --meta '<value>'`
  Then the command exits non-zero
  And stderr indicates --meta must be a JSON object
  And workload.json contains zero items

  Examples:
    | value      |
    | ["a","b"]  |
    | "a string" |
    | 42         |
    | true       |
    | null       |
```

```gherkin
# REQ-05
Scenario: list against a legacy workload (no meta on items) succeeds without rewrite
  Given a workload.json on disk whose items have no "meta" key
  And the file's exact byte content is recorded
  When I run `list`
  Then the command exits 0
  And the rendered output names the items
  And workload.json on disk is byte-for-byte identical to the recorded snapshot
```

```gherkin
# REQ-06
Scenario: rename preserves existing meta verbatim
  Given an initialised workload with item "alpha" whose meta is {"swc:status":{"stage":"plan"}}
  When I run `rename 1 "renamed"`
  Then the command exits 0
  And the item's title is "renamed"
  And the item's "meta" equals {"swc:status": {"stage": "plan"}}

# REQ-06
Scenario: delete a sibling preserves remaining items' meta
  Given items A, B, C where B has meta {"k": "v"}
  When I delete A
  Then B's meta on disk equals {"k": "v"}

# REQ-06
Scenario: move preserves the item's meta through reparent
  Given an item at 2.3 with meta {"k": "v"}
  When I run `move 2.3 to 1.1`
  Then the moved item's meta equals {"k": "v"}
```

```gherkin
# REQ-07
Scenario: add without --meta yields meta: {} even when siblings lack meta
  Given a legacy workload with a single item lacking the "meta" key
  When I run `add "new sibling"`
  Then the command exits 0
  And the new item's "meta" equals {}
  And the existing legacy item still lacks a "meta" key
```

```gherkin
# REQ-08
Scenario Outline: parse_bool_flag accepts case-insensitive true/false
  When I call parse_bool_flag(<input>)
  Then the return value equals <expected>

  Examples:
    | input    | expected |
    | "true"   | True     |
    | "True"   | True     |
    | "TRUE"   | True     |
    | "false"  | False    |
    | "False"  | False    |

# REQ-08
Scenario Outline: parse_bool_flag rejects everything else
  When I call parse_bool_flag(<input>)
  Then a CLIError is raised

  Examples:
    | input  |
    | "yes"  |
    | "0"    |
    | "1"    |
    | ""     |
    | "True " |
```

```gherkin
# REQ-09
Scenario: parse_meta_json returns the parsed object
  When I call parse_meta_json('{"a":1}')
  Then the return value equals {"a": 1}

# REQ-09
Scenario Outline: parse_meta_json rejects malformed JSON or non-object values
  When I call parse_meta_json(<input>)
  Then a CLIError is raised

  Examples:
    | input         |
    | "{bad json"   |
    | "\"string\""  |
    | "[1,2,3]"     |
    | "42"          |
    | "true"        |
    | "null"        |
```

```gherkin
# REQ-10
Scenario: existing schema validation already happens — keep the pin
  Given a workload.json with an item whose "meta" field is the string "oops"
  When any read command loads the file
  Then the CLI exits non-zero with the existing "invalid workload" error path
```

## Validation Rules

| Field            | Type             | Required          | Rules                                                                                            |
| ---------------- | ---------------- | ----------------- | ------------------------------------------------------------------------------------------------ |
| `--meta` (value) | JSON object      | No                | Must parse as valid JSON; parsed value MUST be a JSON object (not array/string/number/bool/null) |
| `meta` (on item) | JSON object      | No (legacy items) | When present, the schema validator already requires JSON-object shape (REQ-10).                  |
| `parse_bool_flag` input | string    | Yes               | Case-insensitive match against the exact tokens `"true"` / `"false"`. No leading/trailing whitespace tolerated. |

Business rules:
- New items always carry `meta: {}` unless `--meta <json>` overrides.
- Reads never write — legacy artefacts stay legacy until a write naturally touches them.
- Mutations never silently introduce or strip a `meta` key on items they touch (unchanged items must be byte-for-byte identical through the mutation, modulo the field being mutated).
