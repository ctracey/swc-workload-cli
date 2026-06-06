"""Tier 1 — e2e tests for the `update-meta <ref> <path> <json-value>` subcommand.

Work item 4.3 — covers REQ-04 through REQ-09, REQ-15 (`update-meta` half),
REQ-17.

Semantics:

- Replace-not-merge at every depth.
- Empty path replaces the whole `meta`; the value MUST be a JSON object.
- Non-empty path accepts any JSON type at the leaf.
- Intermediate object creation when missing.
- Intermediate that exists but is not an object → error, no write.
- Unknown ref → error, no write.
- Legacy item (no `meta`) gets a `meta` field as a side effect of writing.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# REQ-04 — update-meta at a leaf accepts every JSON type
# ---------------------------------------------------------------------------


def test_update_meta_leaf_string(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "k", '"hello"')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"k": "hello"}


def test_update_meta_leaf_number(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "k", "42")
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"k": 42}


def test_update_meta_leaf_boolean(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update-meta", "1", "k", "true").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": True}


def test_update_meta_leaf_null(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update-meta", "1", "k", "null").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": None}


def test_update_meta_leaf_array(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update-meta", "1", "k", "[1,2,3]").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": [1, 2, 3]}


def test_update_meta_leaf_empty_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update-meta", "1", "k", "{}").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": {}}


def test_update_meta_leaf_nested_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update-meta", "1", "k", '{"a":1,"b":[true,null]}').returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "k": {"a": 1, "b": [True, None]}
    }


# REQ-04 — replace-not-merge at a subtree
def test_update_meta_replace_subtree_drops_sibling_keys(swcw_ready):
    run, workload = swcw_ready
    run(
        "add",
        "first",
        "--meta",
        '{"swc:status":{"stage":"plan","started_at":"t0"}}',
    )
    result = run("update-meta", "1", "swc:status", '{"stage":"review"}')
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"swc:status": {"stage": "review"}}


# REQ-04 — partial leaf write preserves siblings under same parent
def test_update_meta_leaf_write_preserves_sibling_keys(swcw_ready):
    run, workload = swcw_ready
    run(
        "add",
        "first",
        "--meta",
        '{"swc:status":{"stage":"plan","started_at":"t0"}}',
    )
    result = run("update-meta", "1", "swc:status.stage", '"review"')
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {
        "swc:status": {"stage": "review", "started_at": "t0"}
    }


# ---------------------------------------------------------------------------
# REQ-05 — empty path replaces whole meta with object; non-object rejected
# ---------------------------------------------------------------------------


def test_update_meta_empty_path_replaces_whole_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"old"}')
    result = run("update-meta", "1", "", '{"b":"new"}')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"b": "new"}


def test_update_meta_empty_path_accepts_empty_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"old"}')
    assert run("update-meta", "1", "", "{}").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {}


def test_update_meta_empty_path_rejects_string(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", '"a string"')
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "object" in msg
    assert workload.read_text() == snapshot


def test_update_meta_empty_path_rejects_array(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", "[1,2]")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_meta_empty_path_rejects_number(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", "42")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_meta_empty_path_rejects_boolean(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", "true")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_meta_empty_path_rejects_null(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", "null")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert workload.read_text() == snapshot


# F-01 (pass 2) — empty-path error messages name the positional argument the
# user actually typed (`<json-value>`), not the `--meta` flag from `add`.
def test_update_meta_empty_path_non_object_error_names_json_value_positional(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "", '"a string"')
    assert result.returncode != 0
    # Stderr must reference the positional, not the (nonexistent on this
    # command) `--meta` flag — that flag belongs to `add`.
    assert "<json-value>" in result.stderr
    assert "--meta" not in result.stderr


def test_update_meta_empty_path_malformed_json_error_names_json_value_positional(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "", "{bad-json")
    assert result.returncode != 0
    assert "<json-value>" in result.stderr
    assert "--meta" not in result.stderr


# ---------------------------------------------------------------------------
# REQ-06 — creates intermediate objects
# ---------------------------------------------------------------------------


def test_update_meta_creates_intermediate_objects(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "a.b.c", '"hello"')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"a": {"b": {"c": "hello"}}}


def test_update_meta_creates_intermediates_alongside_existing_keys(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":{"existing":"kept"}}')
    result = run("update-meta", "1", "a.b.c", "1")
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {
        "a": {"existing": "kept", "b": {"c": 1}}
    }


# ---------------------------------------------------------------------------
# REQ-07 — intermediate is not an object → error, no write
# ---------------------------------------------------------------------------


def test_update_meta_non_object_intermediate_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"leaf-string"}')
    snapshot = workload.read_text()
    result = run("update-meta", "1", "a.b", '"x"')
    assert result.returncode != 0
    # Message should identify the offending intermediate path.
    assert "a" in result.stderr
    assert workload.read_text() == snapshot


def test_update_meta_deeper_non_object_intermediate_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":{"b":42}}')
    snapshot = workload.read_text()
    result = run("update-meta", "1", "a.b.c", '"x"')
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# REQ-08 — malformed JSON → error, no write
# ---------------------------------------------------------------------------


def test_update_meta_malformed_json_rejects_without_writing(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "k", "{bad-json")
    assert result.returncode != 0
    assert "json" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_meta_malformed_json_at_empty_path_rejects_without_writing(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "1", "", "{bad-json")
    assert result.returncode != 0
    assert "json" in result.stderr.lower()
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# REQ-09 — unknown ref → error, no write
# ---------------------------------------------------------------------------


def test_update_meta_unknown_ref_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "99", "k", '"v"')
    assert result.returncode != 0
    assert "99" in result.stderr or "not found" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_meta_unknown_hash_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update-meta", "deadbee", "k", '"v"')
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# REQ-15 — legacy item (no meta field) gains meta on write
# ---------------------------------------------------------------------------


LEGACY_WORKLOAD = {
    "items": [
        {
            "id": "alpha01",
            "title": "alpha",
            "status": "not-started",
            "children": [],
        }
    ]
}


def _write_legacy(workload):
    raw = json.dumps(LEGACY_WORKLOAD, indent=2) + "\n"
    workload.write_text(raw)
    return raw


def test_update_meta_against_legacy_item_creates_meta_field(swcw):
    run, workload = swcw
    _write_legacy(workload)
    result = run("update-meta", "1", "k", '"v"')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"k": "v"}


def test_update_meta_empty_path_against_legacy_item_replaces_root(swcw):
    run, workload = swcw
    _write_legacy(workload)
    result = run("update-meta", "1", "", '{"k":"v"}')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"k": "v"}


# ---------------------------------------------------------------------------
# REQ-17 — JSON output shape is {id, path, value}
# ---------------------------------------------------------------------------


def test_update_meta_json_output_shape(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    on_disk_before = json.loads(workload.read_text())
    item_id = on_disk_before["items"][0]["id"]

    result = run("update-meta", "1", "k", '"hello"', "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"id": item_id, "path": "k", "value": "hello"}


def test_update_meta_json_output_value_is_parsed_verbatim(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "k", "[1,2,3]", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["path"] == "k"
    assert payload["value"] == [1, 2, 3]


def test_update_meta_empty_path_json_output_uses_empty_path_string(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "", '{"k":"v"}', "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["path"] == ""
    assert payload["value"] == {"k": "v"}


# ---------------------------------------------------------------------------
# Text output sanity
# ---------------------------------------------------------------------------


def test_update_meta_text_output_mentions_id_and_path(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update-meta", "1", "k", '"v"')
    assert result.returncode == 0, result.stderr
    on_disk = json.loads(workload.read_text())
    item_id = on_disk["items"][0]["id"]
    assert item_id in result.stdout
