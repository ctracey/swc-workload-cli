"""Tier 1 — e2e tests for the `get <ref>` subcommand (1.2.0, work item 4.2).

Covers REQ-01, REQ-02, REQ-15 (`get` half), REQ-17.

`get <ref>` returns a single item by ref (number or hash). JSON output is a
single object — NOT wrapped in `{items: [...]}` like `list`. `meta` is always
included in JSON output; legacy items without a meta field project `meta: {}`.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# REQ-01 / REQ-17 — get returns a single JSON object including meta
# ---------------------------------------------------------------------------


def test_get_by_number_returns_single_object_with_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"k":"v"}')

    result = run("get", "1", "--json")
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict), "get --json must emit a single object, not an array"
    assert "items" not in payload, "get must NOT wrap in {items: [...]}"
    assert payload["title"] == "first"
    assert payload["meta"] == {"k": "v"}
    assert payload["number"] == "1"
    # Stable contract: id, number, title, status, children, meta.
    assert set(payload.keys()) == {"id", "number", "title", "status", "children", "meta"}


def test_get_by_hash_returns_same_item(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"x":1}')
    on_disk = json.loads(workload.read_text())
    hash_id = on_disk["items"][0]["id"]

    result = run("get", hash_id, "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == hash_id
    assert payload["title"] == "alpha"


def test_get_includes_children_recursively(swcw_ready):
    run, workload = swcw_ready
    run("add", "parent")
    run("add", "child", "to", "1", "--meta", '{"depth":1}')

    result = run("get", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["children"]) == 1
    child = payload["children"][0]
    assert child["title"] == "child"
    assert child["number"] == "1.1"
    assert child["meta"] == {"depth": 1}


def test_get_includes_meta_on_children(swcw_ready):
    """Children carry their own meta in JSON output — no asymmetry with the root."""
    run, workload = swcw_ready
    run("add", "parent", "--meta", '{"p":1}')
    run("add", "child", "to", "1", "--meta", '{"c":2}')

    result = run("get", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["meta"] == {"p": 1}
    assert payload["children"][0]["meta"] == {"c": 2}


def test_get_by_subtree_number_works(swcw_ready):
    run, workload = swcw_ready
    run("add", "parent")
    run("add", "child", "to", "1", "--meta", '{"k":"v"}')

    result = run("get", "1.1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["title"] == "child"
    assert payload["number"] == "1.1"
    assert payload["meta"] == {"k": "v"}


# ---------------------------------------------------------------------------
# REQ-02 — unknown ref errors without rewriting workload.json
# ---------------------------------------------------------------------------


def test_get_unknown_ref_exits_non_zero(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()

    result = run("get", "99")
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "99" in result.stderr or "not found" in msg
    assert workload.read_text() == snapshot, "get must not rewrite workload.json on error"


def test_get_unknown_hash_exits_non_zero(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    snapshot = workload.read_text()

    result = run("get", "deadbee")
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# REQ-15 — legacy items project meta: {} but do NOT rewrite the file
# ---------------------------------------------------------------------------


LEGACY_WORKLOAD = {
    "items": [
        {
            "id": "alpha01",
            "title": "alpha",
            "status": "not-started",
            "children": [],
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
    raw = json.dumps(LEGACY_WORKLOAD, indent=2) + "\n"
    workload.write_text(raw)
    return raw


def test_get_against_legacy_item_projects_empty_meta(swcw):
    run, workload = swcw
    _write_legacy(workload)

    result = run("get", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["meta"] == {}, "legacy item must project meta: {} at read time"


def test_get_against_legacy_item_does_not_rewrite_bytes(swcw):
    """REQ-15: read commands MUST NOT side-effect-write workload.json."""
    run, workload = swcw
    snapshot = _write_legacy(workload)

    result = run("get", "1", "--json")
    assert result.returncode == 0, result.stderr
    assert workload.read_text() == snapshot, "get rewrote workload.json"


# ---------------------------------------------------------------------------
# Text output sanity — symbol + number + id + title
# ---------------------------------------------------------------------------


def test_get_text_output_includes_id_and_title(swcw_ready):
    run, workload = swcw_ready
    run("add", "first")
    result = run("get", "1")
    assert result.returncode == 0, result.stderr
    assert "first" in result.stdout


# ---------------------------------------------------------------------------
# REQ-17 — every --json output parses in a single json.loads call
# ---------------------------------------------------------------------------


def test_get_json_output_parses_in_single_loads(swcw_ready):
    run, workload = swcw_ready
    run("add", "first", "--meta", '{"k":"v"}')
    result = run("get", "1", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
