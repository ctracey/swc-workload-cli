"""Tier 1 — e2e tests for `find-by-meta <path> <pattern>` (pattern mode).

Work item 4.5 — covers REQ-11, REQ-12, REQ-14, REQ-17 (pattern shape).

Pattern mode: match items where the dotted `<path>` resolves to a STRING
value AND `re.search(pattern, value)` matches. Missing path / non-string
leaf is a silent miss (no error, no match). Invalid regex → CLIError
before any file read happens.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# REQ-11 — pattern mode matches string leaves only
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_matches_anchored_string_leaf(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')
    run("add", "beta", "--meta", '{"k":"beta"}')

    result = run("find-by-meta", "k", "^al", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


def test_find_by_meta_pattern_substring_match_unanchored(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')
    run("add", "aloha", "--meta", '{"k":"aloha"}')

    result = run("find-by-meta", "k", "al", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = sorted(m["title"] for m in payload["matches"])
    assert titles == ["aloha", "alpha"]


def test_find_by_meta_pattern_anchor_excludes_unanchored_matches(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')
    run("add", "aloha", "--meta", '{"k":"aloha"}')

    result = run("find-by-meta", "k", "^alp", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


def test_find_by_meta_pattern_matches_nested_path(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"swc:status":{"stage":"plan"}}')
    run("add", "beta", "--meta", '{"swc:status":{"stage":"review"}}')

    result = run("find-by-meta", "swc:status.stage", "plan", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


# ---------------------------------------------------------------------------
# REQ-12 — silently skip missing path / non-string leaf
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_silently_skips_non_string_leaf(swcw_ready):
    """Number / boolean / null / array / object at the leaf is silently dropped."""
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":"hit"}')
    run("add", "b", "--meta", '{"k":42}')
    run("add", "c", "--meta", '{"k":true}')
    run("add", "d", "--meta", '{"k":null}')
    run("add", "e", "--meta", '{"k":[1,2,3]}')
    run("add", "f", "--meta", '{"k":{"nested":"x"}}')

    result = run("find-by-meta", "k", "hit", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["a"]
    assert result.stderr == "" or result.stderr.strip() == ""


def test_find_by_meta_pattern_silently_skips_missing_path(swcw_ready):
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":"hit"}')
    run("add", "b", "--meta", '{}')
    run("add", "c", "--meta", '{"other":"value"}')

    result = run("find-by-meta", "k", "hit", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["a"]


def test_find_by_meta_pattern_silently_skips_missing_intermediate(swcw_ready):
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"a":{"b":"hit"}}')
    run("add", "b", "--meta", '{"a":"leaf"}')  # `a` is not an object

    result = run("find-by-meta", "a.b", "hit", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["a"]


def test_find_by_meta_pattern_empty_match_list_when_nothing_matches(swcw_ready):
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":42}')
    run("add", "b", "--meta", '{}')

    result = run("find-by-meta", "k", "any", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"matches": []}


# ---------------------------------------------------------------------------
# REQ-14 — invalid regex → error, workload.json unchanged
# ---------------------------------------------------------------------------


def test_find_by_meta_invalid_regex_errors_without_writing(swcw_ready):
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":"v"}')
    snapshot = workload.read_text()

    result = run("find-by-meta", "k", "[")
    assert result.returncode != 0
    msg = result.stderr.lower()
    assert "regex" in msg or "pattern" in msg
    assert workload.read_text() == snapshot


def test_find_by_meta_invalid_regex_errors_with_json_flag(swcw_ready):
    """Failure mode is the same with `--json` — non-zero exit, no stdout JSON."""
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"k":"v"}')
    snapshot = workload.read_text()

    result = run("find-by-meta", "k", "[", "--json")
    assert result.returncode != 0
    assert workload.read_text() == snapshot


# ---------------------------------------------------------------------------
# Pattern mode — meta always included in JSON output
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_json_includes_meta(swcw_ready):
    """JSON output always carries the full meta blob."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')

    result = run("find-by-meta", "k", "alpha", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert match["meta"] == {"k": "alpha"}


# ---------------------------------------------------------------------------
# Array support — pattern matches any string element in an array leaf
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_matches_string_element_in_array(swcw_ready):
    """Pattern mode hits when any string element of an array leaf matches."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"tags":["python","web"]}')
    run("add", "beta", "--meta", '{"tags":["java","web"]}')

    result = run("find-by-meta", "tags", "python", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


def test_find_by_meta_pattern_array_all_elements_checked(swcw_ready):
    """Any element in the array can satisfy the pattern."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"tags":["python","web"]}')

    result = run("find-by-meta", "tags", "web", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["matches"]) == 1


def test_find_by_meta_pattern_array_non_string_elements_skipped(swcw_ready):
    """Non-string elements in an array are silently skipped; string ones still match."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"tags":["hit",42,true,null]}')

    result = run("find-by-meta", "tags", "hit", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["matches"]) == 1


def test_find_by_meta_pattern_whole_array_matched_as_json_string(swcw_ready):
    """Pattern can match the whole array's JSON string representation."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"a":[1,2,3]}')
    run("add", "beta", "--meta", '{"a":[4,5,6]}')

    result = run("find-by-meta", "a", r"^\[1, 2, 3\]$", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


def test_find_by_meta_pattern_numeric_array_elements_match_via_json_string(swcw_ready):
    """Numeric elements in an array are coerced to JSON string for matching."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"tags":[1,2,3]}')

    result = run("find-by-meta", "tags", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["matches"]) == 1


def test_find_by_meta_pattern_scalar_leaf_matched_as_json_string(swcw_ready):
    """Number / bool / null at the leaf is coerced to JSON string for matching."""
    run, workload = swcw_ready
    run("add", "a", "--meta", '{"count":42}')
    run("add", "b", "--meta", '{"flag":true}')
    run("add", "c", "--meta", '{"val":null}')

    r1 = run("find-by-meta", "count", "42", "--json")
    assert json.loads(r1.stdout)["matches"][0]["title"] == "a"

    r2 = run("find-by-meta", "flag", "true", "--json")
    assert json.loads(r2.stdout)["matches"][0]["title"] == "b"

    r3 = run("find-by-meta", "val", "null", "--json")
    assert json.loads(r3.stdout)["matches"][0]["title"] == "c"


def test_find_by_meta_pattern_index_into_array_via_path(swcw_ready):
    """Bracket notation indexes into an array — matches the indexed element."""
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"tags":["python","web"]}')
    run("add", "beta", "--meta", '{"tags":["java","web"]}')

    result = run("find-by-meta", "tags[0]", "python", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    titles = [m["title"] for m in payload["matches"]]
    assert titles == ["alpha"]


# ---------------------------------------------------------------------------
# REQ-17 — JSON output parses in single json.loads call
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_json_output_parses_in_single_loads(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"v"}')
    result = run("find-by-meta", "k", "v", "--json")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "matches" in payload
