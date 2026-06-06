"""Tier 1 — e2e tests for `find-by-meta <path>` (presence mode).

Work item 4.4 — covers REQ-10, REQ-13 (default + `--meta true`),
REQ-15 (`find-by-meta` half), REQ-17 (presence shape).

Presence mode: match items where the dotted `<path>` resolves to any
value inside the item's `meta` — including falsy values (`None`, `0`,
`False`, `""`). The output shape mirrors `find`: `{matches: [...]}`.

`--meta true|false` controls whether each match entry includes the
item's full `meta` blob; default is `false`.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# REQ-10 — presence mode hits items with the path resolved
# ---------------------------------------------------------------------------


def _setup_three_items(run):
    """Seed A/B/C with distinct meta shapes used across presence tests."""
    run("add", "alpha", "--meta", '{"swc:status":{"stage":"plan"}}')
    run("add", "beta", "--meta", "{}")
    run("add", "gamma", "--meta", '{"swc:other":{}}')


def test_find_by_meta_presence_matches_items_with_path_resolved(swcw_ready):
    run, workload = swcw_ready
    _setup_three_items(run)

    result = run("find-by-meta", "swc:status", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


def test_find_by_meta_presence_at_empty_path_matches_items_with_meta(swcw_ready):
    """REQ-10 + spec test journey: empty path matches every item that has meta."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    run("add", "beta", "--meta", "{}")

    result = run("find-by-meta", "", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = sorted(m["title"] for m in payload["matches"])
    # Both A and B have a meta field (even if {}).
    assert titles == ["alpha", "beta"]


def test_find_by_meta_presence_respects_falsy_values(swcw_ready):
    """REQ-10 + spec journey: falsy values at the path count as a hit."""
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":null}')
    run("add", "b", "--meta", '{"k":0}')
    run("add", "c", "--meta", "{}")

    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = sorted(m["title"] for m in payload["matches"])
    assert titles == ["a", "b"]


def test_find_by_meta_presence_at_nested_path(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"a":{"b":1}}')
    run("add", "beta", "--meta", '{"a":{"c":1}}')
    run("add", "gamma", "--meta", "{}")

    result = run("find-by-meta", "a.b", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = sorted(m["title"] for m in payload["matches"])
    assert titles == ["alpha"]


def test_find_by_meta_presence_returns_empty_on_no_matches(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "absent", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"matches": []}


def test_find_by_meta_presence_includes_descendants(swcw_ready):
    """Walks the whole tree, not just top-level items."""
    run, workload = swcw_ready
    run("add", "parent")
    run("add", "child", "to", "1", "--meta", '{"k":"v"}')

    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["child"]


# ---------------------------------------------------------------------------
# REQ-13 — --meta true|false controls inclusion of the meta blob
# ---------------------------------------------------------------------------


def test_find_by_meta_default_omits_meta_blob(swcw_ready):
    """Spec table: `find-by-meta` defaults to `--meta false`."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')

    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert "meta" not in match, "default for find-by-meta must be --meta false"


def test_find_by_meta_meta_true_includes_meta_blob(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')

    result = run("find-by-meta", "k", "--meta", "true", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert match["meta"] == {"k": "v"}


def test_find_by_meta_meta_false_explicit_omits(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')

    result = run("find-by-meta", "k", "--meta", "false", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert "meta" not in match


def test_find_by_meta_invalid_meta_flag_value_errors(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k", "--meta", "maybe", "--json")
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Match-entry shape — {id, number, title, status[, meta]}
# ---------------------------------------------------------------------------


def test_find_by_meta_match_entry_shape_default(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert set(match.keys()) == {"id", "number", "title", "status"}
    assert match["title"] == "alpha"
    assert match["number"] == "1"


def test_find_by_meta_match_entry_shape_with_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k", "--meta", "true", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert set(match.keys()) == {"id", "number", "title", "status", "meta"}


# ---------------------------------------------------------------------------
# REQ-15 — legacy items (no meta field) → empty matches, no rewrite
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
    raw = json.dumps(LEGACY_WORKLOAD, indent=2) + "\n"
    workload.write_text(raw)
    return raw


def test_find_by_meta_against_legacy_workload_returns_empty(swcw):
    """REQ-15: items without a meta field never match."""
    run, workload = swcw
    _write_legacy(workload)

    result = run("find-by-meta", "swc:status", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"matches": []}


def test_find_by_meta_against_legacy_workload_does_not_rewrite_bytes(swcw):
    """REQ-15: read command MUST NOT rewrite workload.json."""
    run, workload = swcw
    snapshot = _write_legacy(workload)

    result = run("find-by-meta", "swc:status", "--json")
    assert result.returncode == 0, result.stderr
    assert workload.read_text() == snapshot


def test_find_by_meta_empty_path_against_legacy_workload_returns_empty(swcw):
    """REQ-15 decision pin: legacy items don't match at any path, including ''."""
    run, workload = swcw
    _write_legacy(workload)

    result = run("find-by-meta", "", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"matches": []}


def test_find_by_meta_mixed_legacy_and_modern_skips_legacy(swcw):
    """One item without meta + one with — only the with-meta item matches."""
    run, workload = swcw
    workload.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "leg1234",
                        "title": "legacy",
                        "status": "not-started",
                        "children": [],
                    },
                    {
                        "id": "mod1234",
                        "title": "modern",
                        "status": "not-started",
                        "children": [],
                        "meta": {"k": "v"},
                    },
                ]
            },
            indent=2,
        )
        + "\n"
    )

    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["modern"]


# ---------------------------------------------------------------------------
# Text output sanity — mirrors `find`
# ---------------------------------------------------------------------------


def test_find_by_meta_text_output_no_matches(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "absent")
    assert result.returncode == 0, result.stderr
    assert "no matches" in result.stdout.lower()


def test_find_by_meta_text_output_with_matches(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k")
    assert result.returncode == 0, result.stderr
    # `sym N (id) title` pattern from find.
    assert "alpha" in result.stdout
    assert "1" in result.stdout


# ---------------------------------------------------------------------------
# REQ-17 — JSON output parses in single json.loads call
# ---------------------------------------------------------------------------


def test_find_by_meta_json_output_parses_in_single_loads(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "matches" in payload
