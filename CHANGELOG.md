# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] — 2026-06-09

### Added

- **`meta` field on every work item.** New items default to `meta: {}`. Legacy items without a `meta` field are read without error and gain the field on their first write. The field is a free-form JSON object; callers own its shape entirely.
- **`add --meta <json>`** — supply a JSON object at creation time instead of setting it in a separate step. Malformed JSON and non-object values are rejected with a non-zero exit and no write.
- **`get <ref>`** — fetch a single item as a JSON object. Always includes the full `meta` blob.
- **`find --meta <path> [pattern]`** — search across items by meta content. Without `pattern`, checks for presence of the path. With `pattern`, treats it as a regex matched against the serialised value. Replaces the removed `find-by-meta` command.
- **`update <ref> <path> <value>`** — unified write command. Routes by path:
  - `title` — rename the item
  - `status` — transition status (accepts canonical values and aliases `todo`, `wip`, `complete`)
  - `meta` — replace the entire meta object (value must be a valid JSON object)
  - `meta.<subpath>` — write a single field using dotted + array-index notation (e.g. `meta.tags[0]`)
- **Plain-text fallback for meta subpath values.** `update <ref> meta.stage plan` stores `"plan"` as a string without requiring shell quoting. JSON is tried first; if parsing fails, the raw text is used as-is.
- **Array index support in meta paths.** Both `find --meta` and `update meta.<path>` accept bracket notation (e.g. `meta.tags[0]`). Paths containing brackets must be quoted in the shell.
- **`--json` always includes the full `meta` blob** for `list`, `get`, `find`, and `summary` outputs.

### Removed

- `rename <ref> <title>` — replaced by `update <ref> title <title>`
- `start <ref>` — replaced by `update <ref> status in-progress`
- `complete <ref>` — replaced by `update <ref> status done`
- `reset <ref>` — replaced by `update <ref> status not-started`
- `update-meta <ref> <path> <value>` — replaced by `update <ref> meta.<path> <value>`
- `find-by-meta <path> [pattern]` — replaced by `find --meta <path> [pattern]`

### Migration from 1.1.x

| Old command | 1.2.0 equivalent |
|---|---|
| `rename <ref> <title>` | `update <ref> title <title>` |
| `start <ref>` | `update <ref> status in-progress` |
| `complete <ref>` | `update <ref> status done` |
| `reset <ref>` | `update <ref> status not-started` |
| `update-meta <ref> <path> <value>` | `update <ref> meta.<path> <value>` |
| `update-meta <ref> "" <json>` | `update <ref> meta <json>` |
| `find-by-meta <path> [pattern]` | `find --meta <path> [pattern]` |

Status aliases (`todo`, `wip`, `complete`) are accepted by `update status`.

---

## [1.1.x] and earlier

See git history for changes prior to 1.2.0.
