"""Tree helpers — items are nested dicts with id, title, status, children."""

from __future__ import annotations

import getpass
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from .cli_error import CLIError

# Hash length for displayed/folder IDs.
HASH_LEN = 7


def make_id(title: str, existing_ids: set[str]) -> str:
    """Hash ID = SHA-256(user + ISO timestamp + title), truncated to 7 hex.

    On collision within the workload, append an incrementing suffix and re-hash.

    Note: the original solution.md scheme included `branch` in the payload to
    anchor IDs to the workload they came from. With the path-driven split,
    `swc-workload` no longer knows the branch. The workload path itself is
    a sufficient anchor at this layer; if a stronger anchor is ever needed it
    can be passed by `swc` as part of the payload.
    """
    user = getpass.getuser()
    suffix = 0
    while True:
        ts = datetime.now(timezone.utc).isoformat()
        payload = f"{user}|{ts}|{title}|{suffix}"
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:HASH_LEN]
        if h not in existing_ids:
            return h
        suffix += 1


def all_ids(items: list[dict]) -> set[str]:
    out: set[str] = set()
    def walk(node_list):
        for node in node_list:
            out.add(node["id"])
            walk(node.get("children", []))
    walk(items)
    return out


def iter_items(items: list[dict]):
    """Yield (item, parent_list, index_in_parent, number_tuple)."""
    def walk(node_list, prefix):
        for idx, node in enumerate(node_list):
            number = prefix + (idx + 1,)
            yield node, node_list, idx, number
            yield from walk(node.get("children", []), number)
    yield from walk(items, ())


def find_by_ref(items: list[dict], ref: str) -> Optional[tuple[dict, list[dict], int, tuple[int, ...]]]:
    """Resolve ref (number like '2.3' or hash ID) to a single item.

    Returns (item, parent_list, index_in_parent, number) or None.
    """
    # ID match takes precedence: an all-digit hash prefix (e.g. "8277899")
    # is also a valid numeric path string, so checking IDs first avoids
    # misreading the hash as a path reference.
    for item, parent_list, idx, number in iter_items(items):
        if item["id"] == ref:
            return item, parent_list, idx, number

    if re.fullmatch(r"\d+(?:\.\d+)*", ref):
        target_number = tuple(int(p) for p in ref.split("."))
        for item, parent_list, idx, number in iter_items(items):
            if number == target_number:
                return item, parent_list, idx, number
    return None


def check_no_sibling_title_collision(
    title: str, siblings: list[dict], exclude_id: Optional[str] = None
) -> None:
    """Reject titles that match a sibling's title (case-insensitive).

    Scope: same parent only. Sibling subtrees may have items with the same
    title. `exclude_id` lets `rename` skip its own item so renaming to the
    current title (or a case variant of it) is not flagged as a collision.
    """
    needle = title.casefold()
    for sib in siblings:
        if exclude_id is not None and sib["id"] == exclude_id:
            continue
        if sib["title"].casefold() == needle:
            raise CLIError(
                f"title {title!r} collides with sibling [{sib['id']}] {sib['title']!r} "
                f"(case-insensitive match)"
            )
