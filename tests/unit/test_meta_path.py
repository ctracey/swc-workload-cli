"""Unit tests for the dotted-path helpers in ``swc_workload.meta``.

Backs requirements REQ-16 (and the helpers REQ-04..REQ-09 build on) for
work item 4 of the 1.2.0 meta feature.

The helpers under test:

- ``parse_path(raw)`` — splits a dotted path string into a tuple of
  segments. ``""`` → ``()``; otherwise split on ``.`` verbatim (``:``
  and other punctuation are valid segment characters per spec).
- ``read_at_path(meta, path)`` — walks a nested dict; returns
  ``(found, value)``. ``found=False`` for missing intermediate / missing
  leaf / non-object intermediate. ``found=True`` for any present value
  including falsy ones (``None``, ``0``, ``False``, ``""``).
- ``write_at_path(meta, path, value)`` — mutates ``meta`` in place.
  Creates missing intermediates as ``{}``. Raises ``CLIError`` when an
  intermediate exists and is not a dict. Empty path is invalid (callers
  must replace the whole ``meta`` themselves in that case).
- ``parse_meta_value(raw)`` — wraps ``json.loads`` with a ``CLIError``
  on parse failure; accepts ANY JSON type (used by ``update-meta`` for
  non-empty paths).
"""

from __future__ import annotations

import pytest

from swc_workload.cli_error import CLIError
from swc_workload.meta import (
    parse_meta_value,
    parse_path,
    read_at_path,
    write_at_path,
)


# ---------------------------------------------------------------------------
# REQ-16 — parse_path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ()),
        ("a", ("a",)),
        ("a.b.c", ("a", "b", "c")),
        ("swc:status.stage", ("swc:status", "stage")),
        # `:` is a literal segment character; only `.` separates segments.
        ("vendor:purpose", ("vendor:purpose",)),
        # Empty segments produced by adjacent dots are preserved as-is —
        # no validation beyond emptiness rules per solution.md.
        ("a..b", ("a", "", "b")),
    ],
)
def test_parse_path_splits_on_dot(raw, expected):
    assert parse_path(raw) == expected


# ---------------------------------------------------------------------------
# REQ-16 — read_at_path
# ---------------------------------------------------------------------------


def test_read_at_path_empty_path_returns_root():
    """An empty path resolves to the meta dict itself, always `found=True`."""
    meta: dict = {}
    assert read_at_path(meta, ()) == (True, {})


def test_read_at_path_empty_path_on_populated_meta_returns_the_dict():
    meta = {"a": 1}
    found, value = read_at_path(meta, ())
    assert found is True
    assert value is meta  # returns the dict by reference; safe because reads


def test_read_at_path_one_segment_hit():
    assert read_at_path({"a": 1}, ("a",)) == (True, 1)


def test_read_at_path_nested_hit():
    assert read_at_path({"a": {"b": 1}}, ("a", "b")) == (True, 1)


def test_read_at_path_returns_dict_value_at_leaf():
    meta = {"a": {"b": {"c": 1}}}
    assert read_at_path(meta, ("a", "b")) == (True, {"c": 1})


def test_read_at_path_missing_leaf_returns_not_found():
    assert read_at_path({"a": {}}, ("a", "b")) == (False, None)


def test_read_at_path_missing_top_level_returns_not_found():
    assert read_at_path({}, ("a", "b")) == (False, None)


def test_read_at_path_non_object_intermediate_returns_not_found():
    """Non-object intermediate is treated as missing for reads (spec)."""
    assert read_at_path({"a": "not-object"}, ("a", "b")) == (False, None)


def test_read_at_path_non_object_intermediate_at_deeper_level():
    assert read_at_path({"a": {"b": 1}}, ("a", "b", "c")) == (False, None)


@pytest.mark.parametrize(
    "value",
    [None, 0, False, ""],
)
def test_read_at_path_present_falsy_value_counts_as_found(value):
    """`found=True` even when the value is `None` / falsy — value vs miss."""
    assert read_at_path({"k": value}, ("k",)) == (True, value)


def test_read_at_path_with_namespace_segment():
    """Colon is a literal segment character — `swc:status` is one segment."""
    meta = {"swc:status": {"stage": "plan"}}
    assert read_at_path(meta, ("swc:status", "stage")) == (True, "plan")


def test_read_at_path_does_not_mutate_input():
    meta = {"a": {"b": 1}}
    read_at_path(meta, ("a", "b"))
    read_at_path(meta, ("a", "missing"))
    read_at_path(meta, ("missing",))
    assert meta == {"a": {"b": 1}}


# ---------------------------------------------------------------------------
# REQ-16 — write_at_path
# ---------------------------------------------------------------------------


def test_write_at_path_creates_intermediate_objects():
    meta: dict = {}
    write_at_path(meta, ("a", "b", "c"), 1)
    assert meta == {"a": {"b": {"c": 1}}}


def test_write_at_path_writes_leaf_value():
    meta: dict = {}
    write_at_path(meta, ("k",), "hello")
    assert meta == {"k": "hello"}


def test_write_at_path_replaces_existing_leaf_value():
    meta = {"a": {"b": "old"}}
    write_at_path(meta, ("a", "b"), "new")
    assert meta == {"a": {"b": "new"}}


def test_write_at_path_replace_not_merge_at_subtree():
    """Writing a dict at a subtree replaces wholly — no shallow merge."""
    meta = {"swc:status": {"stage": "plan", "started_at": "t0"}}
    write_at_path(meta, ("swc:status",), {"stage": "review"})
    assert meta == {"swc:status": {"stage": "review"}}


def test_write_at_path_accepts_any_json_type_at_leaf():
    """Leaves may be objects, arrays, strings, numbers, bools, null."""
    meta: dict = {}
    write_at_path(meta, ("k",), {"nested": True})
    assert meta == {"k": {"nested": True}}

    meta = {}
    write_at_path(meta, ("k",), [1, 2, 3])
    assert meta == {"k": [1, 2, 3]}

    meta = {}
    write_at_path(meta, ("k",), None)
    assert meta == {"k": None}


def test_write_at_path_creates_intermediates_alongside_existing_siblings():
    """Existing co-resident keys at the intermediate level are preserved."""
    meta = {"a": {"existing": "kept"}}
    write_at_path(meta, ("a", "b", "c"), 1)
    assert meta == {"a": {"existing": "kept", "b": {"c": 1}}}


def test_write_at_path_empty_path_raises_cli_error():
    """Empty path is invalid for write_at_path; callers handle root replacement."""
    meta: dict = {}
    with pytest.raises(CLIError):
        write_at_path(meta, (), {"anything": True})
    # meta untouched.
    assert meta == {}


def test_write_at_path_non_object_intermediate_raises_cli_error():
    meta = {"a": "not-object"}
    with pytest.raises(CLIError) as excinfo:
        write_at_path(meta, ("a", "b"), 1)
    # Message identifies the offending path/segment for the user.
    msg = str(excinfo.value)
    assert "a" in msg


def test_write_at_path_non_object_intermediate_leaves_input_unchanged():
    meta = {"a": "not-object"}
    with pytest.raises(CLIError):
        write_at_path(meta, ("a", "b"), 1)
    assert meta == {"a": "not-object"}


def test_write_at_path_non_object_intermediate_at_deeper_level():
    meta = {"a": {"b": "leaf"}}
    with pytest.raises(CLIError):
        write_at_path(meta, ("a", "b", "c"), 1)
    assert meta == {"a": {"b": "leaf"}}


# ---------------------------------------------------------------------------
# REQ-04 — parse_meta_value (accepts any JSON type)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('"a string"', "a string"),
        ("42", 42),
        ("3.14", 3.14),
        ("true", True),
        ("false", False),
        ("null", None),
        ("[1,2,3]", [1, 2, 3]),
        ('{"a":1}', {"a": 1}),
        ('{}', {}),
        ('[]', []),
    ],
)
def test_parse_meta_value_accepts_every_json_type(raw, expected):
    assert parse_meta_value(raw) == expected


def test_parse_meta_value_rejects_malformed_json():
    with pytest.raises(CLIError) as excinfo:
        parse_meta_value("{bad-json")
    msg = str(excinfo.value).lower()
    assert "json" in msg
