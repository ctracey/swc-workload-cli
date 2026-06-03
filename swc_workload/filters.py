"""Filter parsing and application for `list`."""

from __future__ import annotations

from .cli_error import CLIError
from .status import STATUS_ALIASES


def normalise_status(value: str) -> str:
    key = value.lower().strip()
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    raise CLIError(
        f"invalid status {value!r}. Use one of: not-started, in-progress, done."
    )


def parse_filter(spec: str) -> tuple[str, list[str]]:
    """Parse 'key:val1,val2' into (key, [normalised values])."""
    if ":" not in spec:
        raise CLIError(f"filter must be key:value form, got {spec!r}")
    key, raw = spec.split(":", 1)
    key = key.strip()
    if key != "status":
        raise CLIError(f"unsupported filter key {key!r}; supported: status")
    values = [normalise_status(v.strip()) for v in raw.split(",") if v.strip()]
    if not values:
        raise CLIError(f"filter {spec!r} has no values")
    return key, values


def apply_filters(
    items_with_numbers: list[tuple[dict, tuple[int, ...]]],
    filters: list[tuple[str, list[str]]],
    excludes: list[tuple[str, list[str]]],
) -> list[dict]:
    """Return a tree containing only items that match include filters AND do
    not match exclude filters. Parents are kept if any descendant matches, but
    children that don't match are dropped.

    Input: list of (node, number) pairs — number is the node's position in the
    unfiltered tree. When at least one filter applies, returns new node dicts
    annotated with `_number` so renderers can display the original references
    rather than reflowed positional ones. With no filters, returns the original
    nodes unchanged.
    """
    def matches(node: dict) -> bool:
        for key, values in filters:
            if key == "status" and node["status"] not in values:
                return False
        for key, values in excludes:
            if key == "status" and node["status"] in values:
                return False
        return True

    def walk(pairs):
        out = []
        for node, number in pairs:
            child_pairs = [
                (c, number + (i + 1,))
                for i, c in enumerate(node.get("children", []))
            ]
            kids = walk(child_pairs)
            if matches(node) or kids:
                out.append({
                    "id": node["id"],
                    "title": node["title"],
                    "status": node["status"],
                    "children": kids,
                    "_number": number,
                })
        return out

    if not filters and not excludes:
        return [node for node, _ in items_with_numbers]
    return walk(items_with_numbers)
