"""`add` — append or insert a new work item."""

from __future__ import annotations

import argparse
import json
import re
from typing import Optional

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..status import STATUS_NOT_STARTED, rollup
from ..tree import all_ids, check_no_sibling_title_collision, find_by_ref, make_id
from ..validation import validate_title
from .command import Command


class AddCommand(Command):
    name = "add"
    help = "Add a work item (optional `to <parent>` or `at <position>`)."
    description = (
        "Add a new work item. The CLI assigns a stable hash ID; numbers are computed\n"
        "at render time and reflow on every structural change.\n"
        "\n"
        "Forms:\n"
        "  add \"<title>\"            — append at top level.\n"
        "  add \"<title>\" to <ref>   — append as the last child of <ref>.\n"
        "  add \"<title>\" at <ref>   — insert at the position <ref>; siblings shift down.\n"
        "                              Out-of-range slot caps at end (same as `move`).\n"
        "\n"
        "Titles must not start with a number-prefix pattern (e.g. `1.1 something`) —\n"
        "numbers are auto-assigned. Sibling-collision check uses the siblings at the\n"
        "target slot (case-insensitive)."
    )
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "title",
            help="Work item title. Must not start with a number-prefix pattern.",
        )
        parser.add_argument(
            "placement",
            nargs="?",
            default=None,
            metavar="[to|at]",
            help=(
                "Optional placement keyword. `to <ref>` appends as the last child of <ref>; "
                "`at <ref>` inserts at that position. Omit to add at top level."
            ),
        )
        parser.add_argument(
            "target",
            nargs="?",
            default=None,
            metavar="[ref]",
            help="Parent or position reference. Required when `to` / `at` is supplied.",
        )

    def execute(self, args) -> int:
        title = args.title
        validate_title(title)

        placement = args.placement
        target = args.target

        if placement is not None and placement not in ("to", "at"):
            raise CLIError(
                f"expected 'to <parent>' or 'at <position>' after title; got {placement!r}"
            )
        if placement is None and target is not None:
            # Shouldn't happen via argparse ordering, but guard anyway.
            raise CLIError("placement keyword required when a target is supplied")
        if placement is not None and target is None:
            raise CLIError(f"`add <title> {placement} <ref>` requires a target after {placement!r}")

        path, data = load_workload_from_args(args)
        items = data["items"]
        existing = all_ids(items)

        insert_idx: Optional[int] = None  # None → append at end of `children`

        if placement == "to":
            found = find_by_ref(items, target)
            if found is None:
                raise CLIError(f"parent {target} not found")
            parent_item, _, _, _ = found
            children = parent_item.setdefault("children", [])
        elif placement == "at":
            if not re.fullmatch(r"\d+(?:\.\d+)*", target):
                raise CLIError(f"`at` target must be a number reference (e.g. `2.3`), got {target!r}")
            parts = [int(p) for p in target.split(".")]
            if any(p < 1 for p in parts):
                raise CLIError(f"`at` positions are 1-based; got {target!r}")
            if len(parts) == 1:
                children = items
            else:
                parent_ref = ".".join(str(p) for p in parts[:-1])
                found = find_by_ref(items, parent_ref)
                if found is None:
                    raise CLIError(f"target parent {parent_ref} does not exist")
                parent_item, _, _, _ = found
                children = parent_item.setdefault("children", [])
            # Cap at end if out of range (matches `move`'s semantics).
            insert_idx = min(parts[-1] - 1, len(children))
        else:
            children = items

        check_no_sibling_title_collision(title, children)

        new_id = make_id(title, existing)
        node = {"id": new_id, "title": title, "status": STATUS_NOT_STARTED, "children": []}
        if insert_idx is None:
            children.append(node)
        else:
            children.insert(insert_idx, node)

        rollup(items)
        save_workload(path, data)

        if args.json:
            print(json.dumps({"id": new_id, "title": title, "status": STATUS_NOT_STARTED}))
        else:
            print(f"added [{new_id}] {title}")
        return 0
