"""Rendering — text and JSON output for workload trees and individual items."""

from __future__ import annotations

from .status import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NOT_STARTED

# Display symbols for terminal-friendly output.
STATUS_SYMBOLS = {
    STATUS_DONE: "✔",
    STATUS_IN_PROGRESS: "▣",
    STATUS_NOT_STARTED: "□",
}
SYM_NOT_STARTED = STATUS_SYMBOLS[STATUS_NOT_STARTED]  # used as fallback symbol


def render_text(items: list[dict], show_ids: bool = True) -> str:
    lines: list[str] = []

    def walk(node_list, prefix):
        for idx, node in enumerate(node_list):
            number = node.get("_number") or (prefix + (idx + 1,))
            num_str = ".".join(str(n) for n in number)
            sym = STATUS_SYMBOLS.get(node["status"], SYM_NOT_STARTED)
            hash_part = f"({node['id']}) " if show_ids else ""
            indent = "  " * (len(number) - 1)
            lines.append(f"{indent}{sym} {num_str} {hash_part}{node['title']}")
            walk(node.get("children", []), number)

    walk(items, ())
    return "\n".join(lines)


def to_json_tree(items: list[dict]) -> list[dict]:
    """Return items annotated with number for JSON output."""
    def walk(node_list, prefix):
        out = []
        for idx, node in enumerate(node_list):
            number = node.get("_number") or (prefix + (idx + 1,))
            out.append({
                "id": node["id"],
                "number": ".".join(str(n) for n in number),
                "title": node["title"],
                "status": node["status"],
                "meta": node.get("meta", {}),
                "children": walk(node.get("children", []), number),
            })
        return out
    return walk(items, ())


def render_item_json(item: dict, number: tuple[int, ...]) -> dict:
    item_number = item.get("_number") or number
    return {
        "id": item["id"],
        "number": ".".join(str(n) for n in item_number),
        "title": item["title"],
        "status": item["status"],
        "meta": item.get("meta", {}),
        "children": [
            render_item_json(c, item_number + (i + 1,))
            for i, c in enumerate(item.get("children", []))
        ],
    }


def render_match_entry(item: dict, number: tuple[int, ...]) -> dict:
    """Return a JSON-serialisable dict for one search match (find / find-by-meta)."""
    return {
        "id": item["id"],
        "number": ".".join(str(n) for n in number),
        "title": item["title"],
        "status": item["status"],
        "meta": item.get("meta", {}),
    }


def render_match_line(item: dict, number: tuple[int, ...]) -> str:
    """Return the single text line for one search match (find / find-by-meta)."""
    num_str = ".".join(str(n) for n in number)
    sym = STATUS_SYMBOLS.get(item["status"], SYM_NOT_STARTED)
    return f"{sym} {num_str} ({item['id']}) {item['title']}"


def render_item_text(item: dict, number: tuple[int, ...], show_ids: bool) -> str:
    lines: list[str] = []
    root_number = item.get("_number") or number

    def walk(node, n):
        node_n = node.get("_number") or n
        num_str = ".".join(str(x) for x in node_n)
        sym = STATUS_SYMBOLS.get(node["status"], SYM_NOT_STARTED)
        hash_part = f"({node['id']}) " if show_ids else ""
        # Indent by depth relative to the root being shown (root depth = 0).
        depth = len(node_n) - len(root_number)
        lines.append(f"{'  ' * depth}{sym} {num_str} {hash_part}{node['title']}")
        for i, c in enumerate(node.get("children", [])):
            walk(c, node_n + (i + 1,))

    walk(item, root_number)
    return "\n".join(lines)
