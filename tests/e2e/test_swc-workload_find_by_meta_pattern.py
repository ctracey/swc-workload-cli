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
    # And stderr should be empty.
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
# Pattern mode with --meta flag (independent of presence mode)
# ---------------------------------------------------------------------------


def test_find_by_meta_pattern_default_omits_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')

    result = run("find-by-meta", "k", "alpha", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert "meta" not in match


def test_find_by_meta_pattern_meta_true_includes_meta(swcw_ready):
    run, workload = swcw_ready
    run("add", "alpha", "--meta", '{"k":"alpha"}')

    result = run("find-by-meta", "k", "alpha", "--meta", "true", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    match = payload["matches"][0]
    assert match["meta"] == {"k": "alpha"}


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
