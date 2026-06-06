# Specs — 4: New subcommands — get, update-meta, find-by-meta

## Users and Personas

- **`swc-workload-mcp` (primary)** — calls the new subcommands as a subprocess from MCP tool implementations. Pins integration tests against exact JSON shapes and exit codes. Goal: round-trip opaque `meta` through `get` / `update-meta` / `find-by-meta` and surface the results to its own callers.
- **Direct CLI user (secondary)** — human authoring workload items and running ad-hoc reads / writes against `meta`. Goal: read a single item including its `meta`; replace pieces of `meta` at known paths; find items by namespace presence or a regex on a string leaf.
- **Legacy-artefact caller** — operates against an artefact whose items predate 1.2.0 and lack a `meta` field. Goal: continue using `find-by-meta` and `get` without errors — missing-path / missing-meta is silently "no match" (find-by-meta) or returns the item with `meta: {}` projected at read time (get; the on-disk file is not rewritten).

## User Journeys

### Happy path — `get <ref>` returns one item including its meta
1. User runs `swc-workload get 1 --json --workload <folder>`.
2. CLI resolves ref `1`, exits 0.
3. stdout is a single JSON object with at least `{id, number, title, status, children, meta}`. Default for `get` is `--meta true`.

### Alternative path — `get <hash>` works the same
1. User runs `swc-workload get <7-char-hash> --json`.
2. CLI returns the matched item exactly as for the numeric ref.

### Alternative path — `get <ref> --meta false` suppresses meta
1. User runs `swc-workload get 1 --meta false --json`.
2. stdout is the same single-object shape WITHOUT the `meta` key.

### Error path — `get` against an unknown ref
1. User runs `swc-workload get 99`.
2. CLI exits non-zero with a stderr message naming `99`. workload.json on disk is unchanged.

### Happy path — `update-meta` with a leaf write
1. Item 1 starts with `meta: {"swc:status":{"stage":"plan"}}`.
2. User runs `update-meta 1 swc:status.stage '"review"'`.
3. CLI exits 0. On disk, item 1's `meta.swc:status.stage` equals `"review"`. The sibling `meta.swc:status` keys are unchanged in structure (still an object containing `stage`).

### Happy path — `update-meta` replaces a whole subtree (replace-not-merge)
1. Item 1 starts with `meta: {"swc:status":{"stage":"plan","started_at":"t0"}}`.
2. User runs `update-meta 1 swc:status '{"stage":"review"}'`.
3. On disk, item 1's `meta` equals `{"swc:status":{"stage":"review"}}` — `started_at` is gone (replace, not merge).

### Happy path — `update-meta` with empty path replaces the whole meta
1. Item 1 starts with `meta: {"swc:status":{"stage":"plan"}}`.
2. User runs `update-meta 1 "" '{"other":{"k":"v"}}'`.
3. On disk, item 1's `meta` equals `{"other":{"k":"v"}}`.

### Happy path — `update-meta` creates intermediate objects
1. Item 1 starts with `meta: {}`.
2. User runs `update-meta 1 a.b.c '"hello"'`.
3. On disk, item 1's `meta` equals `{"a":{"b":{"c":"hello"}}}`.

### Happy path — `update-meta` accepts every JSON leaf type
1. User runs each of `update-meta 1 k '"s"'`, `... k 42`, `... k true`, `... k null`, `... k '[1,2]'`, `... k '{}'`.
2. Each exits 0 and persists the supplied JSON value verbatim at that path.

### Error path — `update-meta` with malformed JSON value
1. User runs `update-meta 1 k '{bad-json'`.
2. CLI exits non-zero with a parse-failure message. workload.json on disk is unchanged.

### Error path — `update-meta` empty path with non-object value
1. User runs `update-meta 1 "" '"a string"'` (or `42`, `null`, `true`, `[1,2]`).
2. CLI exits non-zero with a message indicating the root must be a JSON object. workload.json on disk is unchanged.

### Error path — `update-meta` against an unknown ref
1. User runs `update-meta 99 k '"v"'`.
2. CLI exits non-zero. workload.json on disk is unchanged.

### Error path — `update-meta` intermediate is not an object
1. Item 1 starts with `meta: {"a":"string-leaf"}`.
2. User runs `update-meta 1 a.b '"x"'`.
3. CLI exits non-zero with a message identifying the non-object intermediate path. workload.json on disk is unchanged. (Protects callers from typos clobbering co-resident data.)

### Happy path — `find-by-meta` presence mode
1. Items A (`meta: {"swc:status":{}}`), B (`meta: {}`), C (`meta: {"swc:other":{}}`) exist.
2. User runs `find-by-meta swc:status --json`.
3. CLI exits 0; output `{matches: [...]}` contains only A. Default `--meta false` — A's entry does NOT include the `meta` blob.

### Happy path — `find-by-meta --meta true` includes the meta blob
1. Same setup as above.
2. User runs `find-by-meta swc:status --meta true --json`.
3. A's match entry includes the full `meta` field.

### Happy path — `find-by-meta` presence at empty path matches every item with meta
1. Items A and B have `meta: {"k":"v"}` and `meta: {}` respectively; C lacks `meta` (legacy).
2. User runs `find-by-meta "" --json`.
3. Output matches A and B (both have `meta` of any shape, including empty); C is omitted (treated as no meta available, no path resolves).
   *Note:* this scenario pins behaviour; if it surfaces ambiguous semantics during implementation, surface to user.

### Happy path — `find-by-meta` presence respects falsy values
1. Item A has `meta: {"k": null}`; item B has `meta: {"k": 0}`; item C has `meta: {}`.
2. User runs `find-by-meta k --json`.
3. A and B match (key resolves to a value, even falsy); C does not match (key absent).

### Happy path — `find-by-meta <path> <pattern>` pattern mode hits string leaves
1. Items A `meta: {"k":"alpha"}`, B `meta: {"k":"beta"}`, C `meta: {"k":42}`, D `meta: {}`.
2. User runs `find-by-meta k '^al' --json`.
3. Only A matches. C is silently skipped (non-string at path). D is silently skipped (missing path).

### Happy path — `find-by-meta` regex anchored and unanchored
1. Items A `meta: {"k":"alpha"}`, B `meta: {"k":"aloha"}`.
2. User runs `find-by-meta k 'al' --json` → both match (substring).
3. User runs `find-by-meta k '^alp' --json` → only A matches.

### Error path — `find-by-meta` invalid regex
1. User runs `find-by-meta k '['`.
2. CLI exits non-zero with a regex-error message. workload.json unchanged.

### Legacy path — `find-by-meta` against items lacking `meta`
1. workload.json contains items with NO `meta` field.
2. User runs `find-by-meta swc:status --json`.
3. CLI exits 0 with `{matches: []}` — no errors, no implicit write to workload.json.

### Internal path — dotted-path helpers in meta.py
1. `parse_path("")` returns `()`. `parse_path("a.b.c")` returns `("a","b","c")`. `parse_path("swc:status.stage")` returns `("swc:status","stage")` — colon is a literal segment character.
2. `read_at_path({}, ())` returns `(True, {})` — empty path is root.
3. `read_at_path({"a":{"b":1}}, ("a","b"))` returns `(True, 1)`.
4. `read_at_path({"a":{}}, ("a","b"))` returns `(False, None)`.
5. `read_at_path({"a":"not-object"}, ("a","b"))` returns `(False, None)` — non-object intermediate is treated as missing for reads.
6. `read_at_path({"k": None}, ("k",))` returns `(True, None)` — `None` at a key is a *value*, not a miss.
7. `write_at_path({}, ("a","b","c"), 1)` mutates input to `{"a":{"b":{"c":1}}}`.
8. `write_at_path({"a":"not-object"}, ("a","b"), 1)` raises `CLIError` — intermediate is not an object.
9. `write_at_path({}, (), <anything>)` raises `CLIError` (or programmer error — callers must not pass empty path; pin the failure mode).

## Requirements

- **REQ-01** — WHEN `get <ref>` is invoked with a resolvable ref, the CLI SHALL return that item's record as a single JSON object (NOT wrapped in an array) on stdout when `--json` is supplied, including `meta` by default.
- **REQ-02** — IF `get <ref>` is invoked with a ref that resolves to no item, THEN the CLI SHALL exit non-zero with a stderr message identifying the ref AND SHALL NOT modify `workload.json`.
- **REQ-03** — WHEN `get <ref> --meta false` is invoked, the CLI SHALL omit the `meta` key from the JSON output.
- **REQ-04** — WHEN `update-meta <ref> <path> <json-value>` is invoked with a non-empty `<path>`, the CLI SHALL parse `<json-value>` as JSON (accepting any JSON type: object, array, string, number, boolean, null) and write that value at `<path>` inside the item's `meta`, replacing any existing value there in full.
- **REQ-05** — WHEN `update-meta <ref> "" <json-value>` is invoked with an empty path, the CLI SHALL require `<json-value>` to be a JSON object and replace the entire `meta` with it.
- **REQ-06** — WHEN `update-meta` is invoked and intermediate path objects do not exist, the CLI SHALL create them as empty objects before writing the leaf.
- **REQ-07** — IF `update-meta` traverses an intermediate path segment whose existing value is not a JSON object, THEN the CLI SHALL exit non-zero with a stderr message identifying the offending path AND SHALL NOT modify `workload.json`.
- **REQ-08** — IF `update-meta` is invoked with malformed JSON in `<json-value>`, THEN the CLI SHALL exit non-zero with a JSON parse-error message AND SHALL NOT modify `workload.json`.
- **REQ-09** — IF `update-meta` is invoked with a ref that resolves to no item, THEN the CLI SHALL exit non-zero AND SHALL NOT modify `workload.json`.
- **REQ-10** — WHEN `find-by-meta <path>` is invoked (presence mode), the CLI SHALL return all items where the dotted `<path>` resolves to any value within their `meta` (including falsy values like `0`, `false`, `null`, `""`).
- **REQ-11** — WHEN `find-by-meta <path> <pattern>` is invoked (pattern mode), the CLI SHALL return all items where the dotted `<path>` resolves to a string value AND `re.search(pattern, value)` matches.
- **REQ-12** — WHILE `find-by-meta` operates against any item, IF the dotted path is missing or the leaf value is not a string (pattern mode), THEN the CLI SHALL silently skip that item (no match, no error).
- **REQ-13** — WHEN `find-by-meta` is invoked with `--meta true`, the CLI SHALL include each matched item's full `meta` blob in the output; the default is `--meta false`.
- **REQ-14** — IF `find-by-meta` is invoked with an invalid regex pattern, THEN the CLI SHALL exit non-zero with a regex-error message AND SHALL NOT modify `workload.json`.
- **REQ-15** — WHEN any of the new subcommands operates against a workload whose items lack a `meta` field (legacy), the CLI SHALL behave as if `meta` were `{}` for read / search purposes AND SHALL NOT rewrite `workload.json` as a side effect of read commands. `update-meta` against a legacy item MAY add the `meta` key (since it is a write).
- **REQ-16** — The `swc_workload.meta` module SHALL expose `parse_path(raw: str) -> tuple[str, ...]`, `read_at_path(meta: dict, path: tuple[str, ...]) -> tuple[bool, Any]`, and `write_at_path(meta: dict, path: tuple[str, ...], value: Any) -> None` per the journeys above.
- **REQ-17** — WHEN any of the new subcommands is invoked with `--json`, the output SHALL be valid JSON parseable in a single `json.loads()` call.

## Acceptance Scenarios

```gherkin
# REQ-01
Scenario: get <ref> returns single object including meta
  Given an item with id "I1" and meta {"k":"v"}
  When I run `get 1 --json`
  Then the command exits 0
  And stdout parses as a JSON object (not array)
  And the object's "meta" equals {"k": "v"}
  And the object's "id" equals "I1"
```

```gherkin
# REQ-02
Scenario: get unknown ref errors without writing
  Given a workload with two items
  When I run `get 99`
  Then the command exits non-zero
  And stderr mentions "99" or "not found"
  And workload.json on disk is byte-for-byte unchanged
```

```gherkin
# REQ-03
Scenario: get --meta false omits meta key
  Given an item with meta {"k":"v"}
  When I run `get 1 --meta false --json`
  Then the command exits 0
  And the JSON object does not contain a "meta" key
```

```gherkin
# REQ-04
Scenario Outline: update-meta at a leaf accepts every JSON type
  Given an item with meta {}
  When I run `update-meta 1 k '<value>'`
  Then the command exits 0
  And the saved item's meta.k equals <expected>

  Examples:
    | value     | expected   |
    | "string"  | "string"   |
    | 42        | 42         |
    | true      | true       |
    | null      | null       |
    | [1,2,3]   | [1, 2, 3]  |
    | {"a":1}   | {"a": 1}   |

# REQ-04
Scenario: update-meta replace-not-merge at a subtree
  Given an item with meta {"swc:status":{"stage":"plan","started_at":"t0"}}
  When I run `update-meta 1 swc:status '{"stage":"review"}'`
  Then the saved item's meta equals {"swc:status":{"stage":"review"}}
  And "started_at" is not present anywhere in meta
```

```gherkin
# REQ-05
Scenario: update-meta empty path replaces whole meta with object
  Given an item with meta {"a":"old"}
  When I run `update-meta 1 "" '{"b":"new"}'`
  Then the saved item's meta equals {"b":"new"}

# REQ-05
Scenario Outline: update-meta empty path rejects non-object value
  Given an item with meta {}
  When I run `update-meta 1 "" '<value>'`
  Then the command exits non-zero
  And stderr indicates the root must be a JSON object
  And workload.json on disk is byte-for-byte unchanged

  Examples:
    | value      |
    | "a string" |
    | 42         |
    | true       |
    | null       |
    | [1, 2]     |
```

```gherkin
# REQ-06
Scenario: update-meta creates intermediate objects
  Given an item with meta {}
  When I run `update-meta 1 a.b.c '"hello"'`
  Then the saved item's meta equals {"a":{"b":{"c":"hello"}}}
```

```gherkin
# REQ-07
Scenario: update-meta refuses to overwrite a non-object intermediate
  Given an item with meta {"a":"leaf-string"}
  When I run `update-meta 1 a.b '"x"'`
  Then the command exits non-zero
  And stderr mentions the path "a"
  And workload.json on disk is byte-for-byte unchanged
```

```gherkin
# REQ-08
Scenario: update-meta with malformed JSON rejects without writing
  Given an item with meta {}
  When I run `update-meta 1 k '{bad-json'`
  Then the command exits non-zero
  And stderr indicates a JSON parse error
  And workload.json on disk is byte-for-byte unchanged
```

```gherkin
# REQ-09
Scenario: update-meta unknown ref rejects without writing
  Given a workload with two items
  When I run `update-meta 99 k '"v"'`
  Then the command exits non-zero
  And workload.json on disk is byte-for-byte unchanged
```

```gherkin
# REQ-10
Scenario: find-by-meta presence mode returns items with the path resolved
  Given item A with meta {"swc:status":{"stage":"plan"}}
  And item B with meta {}
  And item C with meta {"swc:other":{}}
  When I run `find-by-meta swc:status --json`
  Then the command exits 0
  And the matches list contains exactly A
  And A's match entry does NOT include a "meta" key (default --meta false)

# REQ-10
Scenario: find-by-meta presence resolves to falsy values as a hit
  Given item A with meta {"k": null}
  And item B with meta {"k": 0}
  And item C with meta {}
  When I run `find-by-meta k --json`
  Then the matches list contains exactly A and B
```

```gherkin
# REQ-11
Scenario: find-by-meta pattern mode regex match on string leaf
  Given item A with meta {"k":"alpha"}
  And item B with meta {"k":"beta"}
  And item C with meta {"k": 42}
  When I run `find-by-meta k '^al' --json`
  Then the matches list contains exactly A
  And C is not in the matches list (non-string at path)
```

```gherkin
# REQ-12
Scenario: find-by-meta silently skips missing-path / non-string in pattern mode
  Given item A with meta {} (missing path)
  And item B with meta {"k": ["array","not-string"]}
  When I run `find-by-meta k 'any' --json`
  Then the command exits 0
  And the matches list is empty
  And stderr is empty
```

```gherkin
# REQ-13
Scenario: find-by-meta --meta true includes the meta blob per match
  Given item A with meta {"k":"v"}
  When I run `find-by-meta k --meta true --json`
  Then A's match entry includes the full "meta" field

# REQ-13
Scenario: find-by-meta default omits meta blob
  Given item A with meta {"k":"v"}
  When I run `find-by-meta k --json`
  Then A's match entry does NOT include a "meta" key
```

```gherkin
# REQ-14
Scenario: find-by-meta invalid regex errors
  Given any workload
  When I run `find-by-meta k '['`
  Then the command exits non-zero
  And stderr mentions regex or pattern
  And workload.json on disk is byte-for-byte unchanged
```

```gherkin
# REQ-15
Scenario: find-by-meta against legacy items (no meta field) returns empty matches
  Given a workload.json on disk whose items have no "meta" key
  And the file's exact byte content is recorded
  When I run `find-by-meta k --json`
  Then the command exits 0
  And the matches list is empty
  And workload.json on disk is byte-for-byte identical to the recorded snapshot

# REQ-15
Scenario: get against a legacy item projects meta: {} but does not rewrite
  Given a workload.json on disk whose item 1 has no "meta" key
  And the file's exact byte content is recorded
  When I run `get 1 --json`
  Then the command exits 0
  And the JSON object's "meta" equals {}
  And workload.json on disk is byte-for-byte identical to the recorded snapshot
```

```gherkin
# REQ-16
Scenario Outline: parse_path round-trips dotted segments verbatim
  When I call parse_path(<input>)
  Then the return value equals <expected>

  Examples:
    | input              | expected                     |
    | ""                 | ()                           |
    | "a"                | ("a",)                       |
    | "a.b.c"            | ("a","b","c")                |
    | "swc:status.stage" | ("swc:status","stage")       |

# REQ-16
Scenario Outline: read_at_path returns (found, value) per the journey table
  When I call read_at_path(<meta>, <path>)
  Then the return value equals <expected>

  Examples:
    | meta                  | path        | expected         |
    | {}                    | ()          | (True, {})       |
    | {"a":{"b":1}}         | ("a","b")   | (True, 1)        |
    | {"a":{}}              | ("a","b")   | (False, None)    |
    | {"a":"not-object"}    | ("a","b")   | (False, None)    |
    | {"k": null}           | ("k",)      | (True, None)     |

# REQ-16
Scenario: write_at_path mutates in place and creates intermediates
  Given an empty dict
  When I call write_at_path(meta, ("a","b","c"), 1)
  Then meta equals {"a":{"b":{"c":1}}}

# REQ-16
Scenario: write_at_path rejects non-object intermediate
  Given meta = {"a":"not-object"}
  When I call write_at_path(meta, ("a","b"), 1)
  Then a CLIError is raised
  And meta is unchanged
```

```gherkin
# REQ-17
Scenario: every --json output parses in a single json.loads call
  Given a workload with items
  When I run any of: get 1 --json, update-meta 1 k '"v"' --json, find-by-meta k --json
  Then stdout parses successfully with a single json.loads() call (no trailing chunks)
```

## Validation Rules

| Input          | Type        | Required          | Rules                                                                                              |
| -------------- | ----------- | ----------------- | -------------------------------------------------------------------------------------------------- |
| `ref` (get / update-meta) | string  | Yes | Resolved by existing `find_by_ref` (dotted-number or 7-char hash). Unknown → non-zero exit.        |
| `path` (update-meta)      | string  | Yes | Empty string allowed and meaningful (root); non-empty split on `.` into segments. No further validation. |
| `path` (find-by-meta)     | string  | Yes | Same as update-meta. Empty-path presence semantics pinned by spec test journey.                    |
| `<json-value>` (update-meta) | string→JSON | Yes | Must parse as JSON. Empty-path branch additionally requires the parsed value to be a JSON object. Otherwise any JSON type is accepted. |
| `<pattern>` (find-by-meta) | string | No | When supplied, compiled via Python `re`. Invalid pattern → non-zero exit with regex-error stderr.   |
| `--meta` flag value       | string | No | Parsed by existing `parse_bool_flag` (`true` / `false`, case-insensitive). Defaults: `get` → true, `find-by-meta` → false. |

Business rules:
- `update-meta` is the ONLY mutating subcommand among the three. `get` and `find-by-meta` are read-only and MUST NOT touch `workload.json` (REQ-15).
- `meta` is opaque — no shape interpretation by the CLI beyond the dotted-path traversal and the JSON-object enforcement at the root.
- Pattern mode matches on string leaves only. Numbers, booleans, nulls, arrays, and objects are silently non-matches (REQ-12), keeping the search surface narrow and predictable.
