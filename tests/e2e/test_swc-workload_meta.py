"""Tier 1 — e2e tests for the per-workitem `meta` field (1.2.0).

Covers work item 3:

- 3.2 — `add` writes `meta: {}` on every new item by default.
- 3.3 — reads tolerate pre-existing items without `meta` (legacy artefacts).
- 3.4 — `add --meta <json>` writes the supplied JSON object verbatim;
  malformed JSON and non-object values are rejected with no write.
- 3.5 — `rename`, `delete`, `move`, and status transitions preserve an
  item's existing `meta` byte-for-byte.

Tests read `workload.json` directly to assert `meta` shape — the read-side
`--meta` flag on `list` / `find` / `summary` lands in work item 5.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# 3.2 — default meta: {} on creation (REQ-01, REQ-07)
# ---------------------------------------------------------------------------


def test_add_default_writes_meta_empty_object(swcw_ready):
    """REQ-01: every new item carries `meta: {}` even without `--meta`."""
    run, workload = swcw_ready
    result = run("add", "first")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {}


def test_add_default_writes_meta_at_every_placement(swcw_ready):
    """Top-level, `to <parent>`, and `at <pos>` placements all default to {}."""
    run, workload = swcw_ready
    run("add", "one")
    run("add", "two")
    run("add", "sub", "to", "1")
    run("add", "first", "at", "1")

    on_disk = json.loads(workload.read_text())
    # Every node in the tree carries meta: {}.
    def assert_meta_empty(nodes):
        for node in nodes:
            assert node["meta"] == {}, f"item {node['title']!r} missing default meta"
            assert_meta_empty(node.get("children", []))
    assert_meta_empty(on_disk["items"])


def test_add_default_meta_independent_of_sibling_state(swcw):
    """REQ-07: new item still gets meta: {} even when sibling lacks meta."""
    run, workload = swcw
    # Seed a legacy-shaped workload directly (no meta on the seeded item).
    workload.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "leg1234",
                        "title": "legacy",
                        "status": "not-started",
                        "children": [],
                    }
                ]
            },
            indent=2,
        )
        + "\n"
    )

    result = run("add", "new sibling")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    legacy, new = on_disk["items"][0], on_disk["items"][1]
    assert "meta" not in legacy, "legacy item should still lack meta — no migration"
    assert new["meta"] == {}, "new item must default to meta: {}"


# ---------------------------------------------------------------------------
# 3.3 — reads tolerate pre-existing items without meta (REQ-05)
# ---------------------------------------------------------------------------


LEGACY_WORKLOAD = {
    "items": [
        {
            "id": "alpha01",
            "title": "alpha",
            "status": "not-started",
            "children": [
                {
                    "id": "alphas1",
                    "title": "alpha sub",
                    "status": "not-started",
                    "children": [],
                }
            ],
        },
        {
            "id": "beta001",
            "title": "beta",
            "status": "done",
            "children": [],
        },
    ]
}


def _write_legacy(workload):
    """Persist the legacy fixture with a stable byte representation."""
    raw = json.dumps(LEGACY_WORKLOAD, indent=2) + "\n"
    workload.write_text(raw)
    return raw


def test_list_against_legacy_workload_exits_zero(swcw):
    run, workload = swcw
    _write_legacy(workload)

    result = run("list")
    assert result.returncode == 0, result.stderr
    assert "alpha" in result.stdout
    assert "beta" in result.stdout


def test_list_against_legacy_workload_does_not_rewrite_bytes(swcw):
    """REQ-05: read commands MUST NOT side-effect-write workload.json."""
    run, workload = swcw
    snapshot = _write_legacy(workload)

    result = run("list")
    assert result.returncode == 0, result.stderr
    assert workload.read_text() == snapshot, "read rewrote workload.json"


def test_find_against_legacy_workload_does_not_rewrite_bytes(swcw):
    run, workload = swcw
    snapshot = _write_legacy(workload)

    result = run("find", "alpha")
    assert result.returncode == 0, result.stderr
    assert workload.read_text() == snapshot


def test_summary_against_legacy_workload_does_not_rewrite_bytes(swcw):
    run, workload = swcw
    snapshot = _write_legacy(workload)

    result = run("summary")
    assert result.returncode == 0, result.stderr
    assert workload.read_text() == snapshot


def test_list_json_against_legacy_workload_round_trips(swcw):
    """The JSON renderer keeps working on the legacy shape — no KeyError."""
    run, workload = swcw
    _write_legacy(workload)

    result = run("list", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [item["title"] for item in payload["items"]]
    assert titles == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# 3.4 — add --meta <json> happy + error paths (REQ-02, REQ-03, REQ-04)
# ---------------------------------------------------------------------------


def test_add_meta_with_simple_object_stores_verbatim(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", '{"swc:status":{"stage":"plan"}}')
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {"swc:status": {"stage": "plan"}}


def test_add_meta_with_nested_object_preserves_shape(swcw_ready):
    run, workload = swcw_ready
    raw = '{"a":{"b":[1,2,{"c":null}],"d":true}}'
    result = run("add", "first", "--meta", raw)
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {
        "a": {"b": [1, 2, {"c": None}], "d": True}
    }


def test_add_meta_with_empty_object_is_equivalent_to_default(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", "{}")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"][0]["meta"] == {}


def test_add_meta_works_with_to_placement(swcw_ready):
    run, workload = swcw_ready
    run("add", "parent")
    result = run(
        "add", "child", "to", "1", "--meta", '{"swc:notes":"hello"}'
    )
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    child = on_disk["items"][0]["children"][0]
    assert child["meta"] == {"swc:notes": "hello"}


def test_add_meta_rejects_malformed_json_without_writing(swcw_ready):
    run, workload = swcw_ready
    before = json.loads(workload.read_text())
    item_count_before = len(before["items"])

    result = run("add", "first", "--meta", "{not-json}")
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "json" in msg or "parse" in msg

    after = json.loads(workload.read_text())
    assert len(after["items"]) == item_count_before, (
        "add should not write workload.json when --meta is invalid"
    )


def test_add_meta_rejects_array_value_without_writing(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", '["a","b"]')
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "object" in msg

    on_disk = json.loads(workload.read_text())
    assert on_disk["items"] == []


def test_add_meta_rejects_string_value_without_writing(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", '"just a string"')
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert json.loads(workload.read_text())["items"] == []


def test_add_meta_rejects_number_value_without_writing(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", "42")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert json.loads(workload.read_text())["items"] == []


def test_add_meta_rejects_boolean_value_without_writing(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", "true")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert json.loads(workload.read_text())["items"] == []


def test_add_meta_rejects_null_value_without_writing(swcw_ready):
    run, workload = swcw_ready
    result = run("add", "first", "--meta", "null")
    assert result.returncode != 0
    assert "object" in result.stderr.lower()
    assert json.loads(workload.read_text())["items"] == []


# Pin the existing JSON-output shape so the legacy contract holds — `add --json`
# still emits {id, title, status} only. Adding `meta` to that shape is item 5.
def test_add_json_output_shape_unchanged_when_meta_supplied(swcw_ready):
    run, workload = swcw_ready
    result = run(
        "add", "first", "--meta", '{"k":"v"}', "--json"
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"id", "title", "status"}


# ---------------------------------------------------------------------------
# 3.5 — update / delete / move / status preserve existing meta (REQ-06)
# ---------------------------------------------------------------------------


NONTRIVIAL_META = {
    "swc:status": {"stage": "plan", "started_at": "2026-06-04T10:00:00Z"},
    "swc:notes": ["a", "b", "c"],
    "owner": {"name": "alice", "tags": [1, 2, 3]},
}


def _meta_of(workload_path, *indices):
    """Walk indices into items[...].children[...] and return the item's `meta`."""
    data = json.loads(workload_path.read_text())
    node = data["items"][indices[0]]
    for i in indices[1:]:
        node = node["children"][i]
    return node["meta"]


def test_update_preserves_existing_meta_byte_for_byte(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", json.dumps(NONTRIVIAL_META))

    result = run("update", "1", "title", "renamed")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    updated = on_disk["items"][0]
    assert updated["title"] == "renamed"
    assert updated["meta"] == NONTRIVIAL_META


def test_delete_sibling_preserves_remaining_items_meta(swcw_ready):
    """Deleting A leaves B's meta intact byte-for-byte."""
    run, workload = swcw_ready
    run("add", "a")
    run("add", "b", "--meta", json.dumps(NONTRIVIAL_META))
    run("add", "c")

    result = run("delete", "1")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    titles = [i["title"] for i in on_disk["items"]]
    assert titles == ["b", "c"]
    assert on_disk["items"][0]["meta"] == NONTRIVIAL_META


def test_move_to_preserves_meta_through_reparent(swcw_ready):
    run, workload = swcw_ready
    run("add", "one")
    run("add", "two")
    run("add", "deep", "to", "2", "--meta", json.dumps(NONTRIVIAL_META))

    # `deep` is at 2.1; move it to top-level position 1.
    result = run("move", "2.1", "to", "1")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    titles = [i["title"] for i in on_disk["items"]]
    assert titles == ["deep", "one", "two"]
    assert on_disk["items"][0]["meta"] == NONTRIVIAL_META


def test_move_direction_preserves_meta(swcw_ready):
    """Direction form (`up` / `down` / `top` / `bottom`) also preserves meta."""
    run, workload = swcw_ready
    run("add", "parent")
    run("add", "a", "to", "1")
    run("add", "b", "to", "1", "--meta", json.dumps(NONTRIVIAL_META))
    run("add", "c", "to", "1")

    result = run("move", "1.2", "up")
    assert result.returncode == 0, result.stderr

    on_disk = json.loads(workload.read_text())
    children = on_disk["items"][0]["children"]
    titles = [c["title"] for c in children]
    assert titles == ["b", "a", "c"]
    assert children[0]["meta"] == NONTRIVIAL_META


def test_status_transitions_preserve_meta(swcw_ready):
    """Status transitions touch `status` only — `meta` must round-trip intact."""
    run, workload = swcw_ready
    run("add", "thing", "--meta", json.dumps(NONTRIVIAL_META))

    assert run("update", "1", "status", "in-progress").returncode == 0
    assert _meta_of(workload, 0) == NONTRIVIAL_META

    assert run("update", "1", "status", "done").returncode == 0
    assert _meta_of(workload, 0) == NONTRIVIAL_META

    assert run("update", "1", "status", "not-started").returncode == 0
    assert _meta_of(workload, 0) == NONTRIVIAL_META
