"""Regression test for find_by_ref's handling of all-digit hash IDs.

Hash IDs are 7 hex chars; ~3.7% of randomly generated IDs are all-digits
(e.g. "8277899") and collide with the dotted numeric-path ref syntax. The
resolver must match IDs before falling back to path resolution, otherwise
all-digit hashes are unreachable by reference.
"""

from __future__ import annotations

from swc_workload.tree import find_by_ref


def _item(item_id: str, title: str, children=None) -> dict:
    return {"id": item_id, "title": title, "status": "_", "children": children or []}


def test_all_digit_hash_id_resolves_to_item_not_path():
    items = [
        _item("aaaaaaa", "first"),
        _item("8277899", "target"),
        _item("bbbbbbb", "third"),
    ]

    result = find_by_ref(items, "8277899")

    assert result is not None
    item, _parent, _idx, _number = result
    assert item["title"] == "target"


def test_numeric_path_still_resolves_when_no_id_matches():
    items = [
        _item("aaaaaaa", "first"),
        _item("bbbbbbb", "second"),
    ]

    result = find_by_ref(items, "2")

    assert result is not None
    item, _parent, _idx, _number = result
    assert item["title"] == "second"
