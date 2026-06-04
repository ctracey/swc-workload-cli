"""Schema validator pins for the optional `meta` field (REQ-05 / REQ-10).

`_validate_shape` is the gate that keeps caller-visible JSON honest. The
1.2.0 work adds an optional `meta` field; the validator must:

- accept items without `meta` (REQ-05 — legacy artefacts load cleanly), and
- reject items whose `meta` is not a JSON object (REQ-10 — no accidental
  weakening of the existing shape contract).
"""

from __future__ import annotations

import pytest

from swc_workload.cli_error import CLIError
from swc_workload.io import _validate_shape


def _data(items):
    return {"items": items}


def _item(meta=...):
    node = {
        "id": "abc1234",
        "title": "thing",
        "status": "not-started",
        "children": [],
    }
    if meta is not ...:
        node["meta"] = meta
    return node


def test_validate_shape_accepts_item_without_meta():
    """REQ-05 — pre-existing items without `meta` keep loading."""
    _validate_shape(_data([_item()]))


def test_validate_shape_accepts_item_with_empty_meta():
    _validate_shape(_data([_item(meta={})]))


def test_validate_shape_accepts_item_with_nested_meta():
    nested = {"swc:status": {"stage": "plan"}, "extra": [1, 2, 3]}
    _validate_shape(_data([_item(meta=nested)]))


@pytest.mark.parametrize(
    "bad_meta",
    [
        "not a dict",
        ["array", "instead"],
        42,
        True,
        None,
    ],
)
def test_validate_shape_rejects_non_object_meta(bad_meta):
    """REQ-10 — when present, `meta` must be a JSON object."""
    with pytest.raises(CLIError) as excinfo:
        _validate_shape(_data([_item(meta=bad_meta)]))
    msg = str(excinfo.value).lower()
    assert "meta" in msg
    assert "object" in msg
