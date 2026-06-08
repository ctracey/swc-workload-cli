"""Tier 1 — e2e tests for the `update <ref> <path> <value>` subcommand.

Covers REQ-04 through REQ-09, REQ-15, REQ-17 plus title and status paths.

Routing:
  update <ref> title <string>         — title validation, sibling collision check
  update <ref> status <string>        — alias resolution, parent rollup
  update <ref> meta <json-object>     — replace entire meta root
  update <ref> meta.<path> <json>     — dotted-path write into meta
  update <ref> id/number ...          — rejected
  update <ref> <unknown> ...          — rejected
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# title path
# ---------------------------------------------------------------------------


def test_update_title_changes_title(swcw_ready):
    run, workload = swcw_ready
    run("add", "original")
    result = run("update", "1", "title", "updated title")
    assert result.returncode == 0, result.stderr
    items = json.loads(run("list", "--json").stdout)["items"]
    assert items[0]["title"] == "updated title"


def test_update_title_preserves_id_and_status(swcw_ready):
    run, workload = swcw_ready
    run("add", "original")
    run("update", "1", "status", "in-progress")
    before_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]
    run("update", "1", "title", "new title")
    item = json.loads(run("list", "--json").stdout)["items"][0]
    assert item["id"] == before_id
    assert item["status"] == "in-progress"


def test_update_title_rejects_number_prefix(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "title", "2.3 bad title")
    assert result.returncode != 0
    assert json.loads(run("list", "--json").stdout)["items"][0]["title"] == "first"


def test_update_title_rejects_duplicate_sibling(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha")
    run("add", "beta")
    result = run("update", "2", "title", "ALPHA")
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "collide" in msg or "alpha" in msg


def test_update_title_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "original")
    item_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]
    result = run("update", "1", "title", "new title", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"id": item_id, "path": "title", "value": "new title"}


# ---------------------------------------------------------------------------
# status path
# ---------------------------------------------------------------------------


def test_update_status_canonical_value(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    result = run("update", "1", "status", "in-progress")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "in-progress"


def test_update_status_alias_wip(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    result = run("update", "1", "status", "wip")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "in-progress"


def test_update_status_alias_todo(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    run("update", "1", "status", "in-progress")
    result = run("update", "1", "status", "todo")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "not-started"


def test_update_status_alias_complete(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    result = run("update", "1", "status", "complete")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "done"


def test_update_status_rejects_invalid(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    result = run("update", "1", "status", "pending")
    assert result.returncode != 0
    assert "invalid status" in result.stderr.lower() or "pending" in result.stderr


def test_update_status_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "item")
    item_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]
    result = run("update", "1", "status", "done", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"id": item_id, "path": "status", "value": "done"}


def test_update_status_triggers_parent_rollup(swcw_ready):
    run, workload = swcw_ready
    run("add", "parent")
    run("add", "child-a", "to", "1")
    run("add", "child-b", "to", "1")
    run("update", "1.1", "status", "done")
    run("update", "1.2", "status", "done")
    items = json.loads(run("list", "--json").stdout)["items"]
    assert items[0]["status"] == "done"


# ---------------------------------------------------------------------------
# meta root path (path = "meta")
# ---------------------------------------------------------------------------


def test_update_meta_root_replaces_whole_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"old"}')
    result = run("update", "1", "meta", '{"b":"new"}')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"b": "new"}


def test_update_meta_root_accepts_empty_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"old"}')
    result = run("update", "1", "meta", "{}")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {}


def test_update_meta_root_rejects_non_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    for bad in ('"a string"', "[1,2]", "42", "true", "null"):
        snapshot = workload.read_text()
        result = run("update", "1", "meta", bad)
        assert result.returncode != 0, f"expected failure for {bad!r}"
        assert "object" in result.stderr.lower()
        assert workload.read_text() == snapshot


def test_update_meta_root_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    item_id = json.loads(workload.read_text())["items"][0]["id"]
    result = run("update", "1", "meta", '{"k":"v"}', "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"id": item_id, "path": "meta", "value": {"k": "v"}}


# ---------------------------------------------------------------------------
# meta subpath — REQ-04: accepts every JSON type at the leaf
# ---------------------------------------------------------------------------


def test_update_meta_subpath_string(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.k", '"hello"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": "hello"}


def test_update_meta_subpath_number(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.k", "42")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": 42}


def test_update_meta_subpath_boolean(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update", "1", "meta.k", "true").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": True}


def test_update_meta_subpath_null(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update", "1", "meta.k", "null").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": None}


def test_update_meta_subpath_array(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update", "1", "meta.k", "[1,2,3]").returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": [1, 2, 3]}


def test_update_meta_subpath_object(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    assert run("update", "1", "meta.k", '{"a":1}').returncode == 0
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": {"a": 1}}


def test_update_meta_replace_subtree_drops_sibling_keys(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"swc:status":{"stage":"plan","started_at":"t0"}}')
    result = run("update", "1", "meta.swc:status", '{"stage":"review"}')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "swc:status": {"stage": "review"}
    }


def test_update_meta_leaf_write_preserves_sibling_keys(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"swc:status":{"stage":"plan","started_at":"t0"}}')
    result = run("update", "1", "meta.swc:status.stage", '"review"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "swc:status": {"stage": "review", "started_at": "t0"}
    }


# ---------------------------------------------------------------------------
# meta subpath — REQ-06: creates intermediate objects
# ---------------------------------------------------------------------------


def test_update_meta_creates_intermediate_objects(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.a.b.c", '"hello"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "a": {"b": {"c": "hello"}}
    }


def test_update_meta_creates_intermediates_alongside_existing_keys(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":{"existing":"kept"}}')
    result = run("update", "1", "meta.a.b.c", "1")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "a": {"existing": "kept", "b": {"c": 1}}
    }


# ---------------------------------------------------------------------------
# meta subpath — REQ-07: non-object intermediate errors without writing
# ---------------------------------------------------------------------------


def test_update_meta_non_object_intermediate_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":"leaf-string"}')
    snapshot = workload.read_text()
    result = run("update", "1", "meta.a.b", '"x"')
    assert result.returncode != 0
    assert "a" in result.stderr
    assert workload.read_text() == snapshot


def test_update_meta_deeper_non_object_intermediate_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"a":{"b":42}}')
    snapshot = workload.read_text()
    result = run("update", "1", "meta.a.b.c", '"x"')
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# meta subpath — invalid JSON falls back to plain string (REQ-08 revised)
# ---------------------------------------------------------------------------


def test_update_meta_malformed_json_stored_as_string(swcw_ready):
    """Invalid JSON is treated as a plain string, not an error."""
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.k", "{bad-json")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": "{bad-json"}


# ---------------------------------------------------------------------------
# REQ-09: unknown ref errors without writing
# ---------------------------------------------------------------------------


def test_update_unknown_ref_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update", "99", "meta.k", '"v"')
    assert result.returncode != 0
    assert "99" in result.stderr or "not found" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_unknown_hash_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update", "deadbee", "meta.k", '"v"')
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# Protected and unknown paths
# ---------------------------------------------------------------------------


def test_update_id_is_rejected(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update", "1", "id", "newid")
    assert result.returncode != 0
    assert "id" in result.stderr.lower()
    assert workload.read_text() == snapshot


def test_update_number_is_rejected(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update", "1", "number", "99")
    assert result.returncode != 0
    assert workload.read_text() == snapshot


def test_update_unknown_path_is_rejected(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()
    result = run("update", "1", "children", "[]")
    assert result.returncode != 0
    assert "unknown field" in result.stderr.lower() or "children" in result.stderr
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# REQ-15: legacy item (no meta field) gains meta on write
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
    result = run("update", "1", "meta.k", '"v"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": "v"}


def test_update_meta_root_against_legacy_item_sets_meta(swcw):
    run, workload = swcw
    _write_legacy(workload)
    result = run("update", "1", "meta", '{"k":"v"}')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"k": "v"}


# ---------------------------------------------------------------------------
# REQ-17: JSON output shape
# ---------------------------------------------------------------------------


def test_update_meta_subpath_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    item_id = json.loads(workload.read_text())["items"][0]["id"]
    result = run("update", "1", "meta.k", '"hello"', "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"id": item_id, "path": "meta.k", "value": "hello"}


def test_update_meta_subpath_json_output_array_value(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.k", "[1,2,3]", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["path"] == "meta.k"
    assert payload["value"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Plain-text fallback for meta subpath values
# ---------------------------------------------------------------------------


def test_update_meta_plain_text_stored_as_string(swcw_ready):
    """Unquoted text that is not valid JSON is stored as a plain string."""
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.stage", "implement")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {"stage": "implement"}


def test_update_meta_plain_text_with_spaces(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.owner", "alice smith")
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"]["owner"] == "alice smith"


def test_update_meta_typed_json_not_affected_by_fallback(swcw_ready):
    """Numbers, booleans, arrays still parse as their JSON types."""
    run, workload = swcw_ready
    run("add", "first")
    run("update", "1", "meta.count", "42")
    run("update", "1", "meta.active", "true")
    run("update", "1", "meta.tags", "[1,2,3]")
    meta = json.loads(workload.read_text())["items"][0]["meta"]
    assert meta["count"] == 42
    assert meta["active"] is True
    assert meta["tags"] == [1, 2, 3]


def test_update_meta_json_string_still_requires_quoting_to_override_type(swcw_ready):
    """'"true"' stores the string "true", not the boolean."""
    run, workload = swcw_ready
    run("add", "first")
    result = run("update", "1", "meta.flag", '"true"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"]["flag"] == "true"


# ---------------------------------------------------------------------------
# Array index writes via bracket notation in meta paths
# ---------------------------------------------------------------------------


def test_update_meta_array_index_write(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"tags":["python","web"]}')
    result = run("update", "1", "meta.tags[0]", '"rust"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "tags": ["rust", "web"]
    }


def test_update_meta_nested_array_index_write(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"steps":[{"name":"build"},{"name":"test"}]}')
    result = run("update", "1", "meta.steps[0].name", '"compile"')
    assert result.returncode == 0, result.stderr
    assert json.loads(workload.read_text())["items"][0]["meta"] == {
        "steps": [{"name": "compile"}, {"name": "test"}]
    }


def test_update_meta_array_index_out_of_bounds_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"tags":["python"]}')
    snapshot = workload.read_text()
    result = run("update", "1", "meta.tags[5]", '"rust"')
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# Text output sanity
# ---------------------------------------------------------------------------


def test_update_meta_text_output_mentions_id(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    item_id = json.loads(workload.read_text())["items"][0]["id"]
    result = run("update", "1", "meta.k", '"v"')
    assert result.returncode == 0, result.stderr
    assert item_id in result.stdout
