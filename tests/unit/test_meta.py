"""Unit tests for ``swc_workload.meta`` — bool flag + meta JSON parsers.

Backs requirements REQ-08 (parse_bool_flag) and REQ-09 (parse_meta_json)
on work item 3 of the 1.2.0 meta feature.
"""

from __future__ import annotations

import pytest

from swc_workload.cli_error import CLIError
from swc_workload.meta import parse_bool_flag, parse_meta_json


# ---------------------------------------------------------------------------
# REQ-08 — parse_bool_flag accepts case-insensitive true/false
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
    ],
)
def test_parse_bool_flag_accepts_case_insensitive_true_false(value, expected):
    assert parse_bool_flag(value) is expected


# REQ-08 — parse_bool_flag rejects everything else, including padded whitespace,
# `1`/`0`, `yes`/`no`, empty string. Strict by design.
@pytest.mark.parametrize(
    "value",
    [
        "yes",
        "no",
        "0",
        "1",
        "",
        "True ",
        " true",
        "tru",
        "falsey",
    ],
)
def test_parse_bool_flag_rejects_everything_else(value):
    with pytest.raises(CLIError):
        parse_bool_flag(value)


# ---------------------------------------------------------------------------
# REQ-09 — parse_meta_json returns the parsed JSON object
# ---------------------------------------------------------------------------


def test_parse_meta_json_returns_simple_object():
    assert parse_meta_json('{"a": 1}') == {"a": 1}


def test_parse_meta_json_returns_empty_object():
    assert parse_meta_json("{}") == {}


def test_parse_meta_json_preserves_nested_object_shape():
    raw = '{"a":{"b":[1,2,{"c":null}],"d":true}}'
    assert parse_meta_json(raw) == {"a": {"b": [1, 2, {"c": None}], "d": True}}


def test_parse_meta_json_preserves_caller_namespace_keys():
    """Caller convention is `vendor:purpose` — keys can contain `:`."""
    raw = '{"swc:status": {"stage": "plan"}}'
    assert parse_meta_json(raw) == {"swc:status": {"stage": "plan"}}


# REQ-09 — parse_meta_json rejects malformed JSON
def test_parse_meta_json_rejects_malformed_json_with_clear_message():
    with pytest.raises(CLIError) as excinfo:
        parse_meta_json("{not-json}")
    msg = str(excinfo.value).lower()
    # Solution.md mandates a "must be valid JSON" framing so MCP tests can grep
    # the error mode.
    assert "valid json" in msg or "json" in msg


# REQ-09 — parse_meta_json rejects non-object JSON values
@pytest.mark.parametrize(
    "value",
    [
        '["a","b"]',
        '"a string"',
        "42",
        "true",
        "false",
        "null",
    ],
)
def test_parse_meta_json_rejects_non_object_values(value):
    with pytest.raises(CLIError) as excinfo:
        parse_meta_json(value)
    msg = str(excinfo.value).lower()
    # Solution.md mandates a "must be a JSON object" framing.
    assert "object" in msg
