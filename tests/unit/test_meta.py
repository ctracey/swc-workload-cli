"""Unit tests for ``swc_workload.meta`` — bool flag + meta JSON parsers.

Backs requirements REQ-08 (parse_bool_flag) and REQ-09 (parse_meta_json)
on work item 3 of the 1.2.0 meta feature.
"""

from __future__ import annotations

import pytest

from swc_workload.cli_error import CLIError
from swc_workload.meta import parse_bool_flag, parse_meta_json, parse_meta_object


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


# ---------------------------------------------------------------------------
# F-01 (pass 2) — parse_meta_json keeps its `--meta` framing for backward
# compatibility, but the underlying parser is now label-aware so callers
# (notably `update-meta` empty-path) can surface the correct positional name.
# ---------------------------------------------------------------------------


def test_parse_meta_json_error_messages_keep_meta_flag_label():
    """`parse_meta_json` is the entry point used by `--meta <json>` callers
    (`add`, `start`/`complete`/`reset` in item 6). Its error messages MUST
    continue to name the `--meta` flag verbatim so MCP integration tests
    that grep for that string keep working.
    """
    # JSON parse failure path.
    with pytest.raises(CLIError) as excinfo:
        parse_meta_json("{not-json}")
    assert "--meta" in str(excinfo.value)

    # Non-object path.
    with pytest.raises(CLIError) as excinfo:
        parse_meta_json('"a string"')
    assert "--meta" in str(excinfo.value)


def test_parse_meta_object_uses_supplied_label_in_errors():
    """`parse_meta_object(raw, label)` is the flag-agnostic core: callers
    pick the label so the user sees the argument they actually typed.
    """
    # Custom label propagated through the parse-failure path.
    with pytest.raises(CLIError) as excinfo:
        parse_meta_object("{not-json}", label="<json-value>")
    msg = str(excinfo.value)
    assert "<json-value>" in msg
    assert "--meta" not in msg
    assert "json" in msg.lower()

    # Custom label propagated through the non-object path.
    with pytest.raises(CLIError) as excinfo:
        parse_meta_object('"a string"', label="<json-value>")
    msg = str(excinfo.value)
    assert "<json-value>" in msg
    assert "--meta" not in msg
    assert "object" in msg.lower()


def test_parse_meta_object_returns_parsed_object():
    """Happy path mirrors parse_meta_json."""
    assert parse_meta_object('{"a": 1}', label="<json-value>") == {"a": 1}
    assert parse_meta_object("{}", label="<json-value>") == {}
