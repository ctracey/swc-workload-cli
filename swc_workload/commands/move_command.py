"""`move` — relocate a work item, relative or absolute."""

from __future__ import annotations

import argparse
import json
import re

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..status import rollup
from ..tree import find_by_ref
from .command import Command

DIRECTIONS = ("up", "down", "top", "bottom")


def _contains_subtree(node: dict, item_id: str) -> bool:
    if node["id"] == item_id:
        return True
    return any(_contains_subtree(c, item_id) for c in node.get("children", []))


class MoveCommand(Command):
    name = "move"
    help = "Move a work item — relative (up|down|top|bottom) or absolute (to <target>)."
    description = (
        "Move a work item. Two forms:\n"
        "  move <ref> <up|down|top|bottom>  — relative shift among siblings; IDs and parent unchanged; numbers reflow.\n"
        "  move <ref> to <target>           — absolute position; may reparent; cycles rejected; both old and new parent renumber."
    )
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)
        parser.add_argument(
            "position_or_direction",
            metavar="direction|to",
            help=(
                "Direction (up|down|top|bottom) for a relative move, or the literal "
                "'to' for an absolute move (followed by target)."
            ),
        )
        parser.add_argument(
            "target",
            nargs="?",
            default=None,
            help=(
                "Destination position — number (e.g. `3.2`). Required after 'to'; "
                "must be omitted with a direction."
            ),
        )

    def execute(self, args) -> int:
        """Two forms dispatched on the second positional:
          move <ref> <up|down|top|bottom>    — relative shift among siblings; IDs unchanged
          move <ref> to <target>             — absolute position; may reparent; cycles rejected
        """
        second = args.position_or_direction

        if second in DIRECTIONS:
            if args.target is not None:
                raise CLIError(
                    f"unexpected token {args.target!r} after direction {second!r}; "
                    f"use `move <ref> {second}` with no target"
                )
            path, data = load_workload_from_args(args)
            items = data["items"]
            found = find_by_ref(items, args.ref)
            if found is None:
                raise CLIError(f"item {args.ref} not found")
            item, parent_list, idx, _ = found

            if second == "up":
                new_idx = max(0, idx - 1)
            elif second == "down":
                new_idx = min(len(parent_list) - 1, idx + 1)
            elif second == "top":
                new_idx = 0
            else:  # bottom
                new_idx = len(parent_list) - 1

            if new_idx != idx:
                parent_list.pop(idx)
                parent_list.insert(new_idx, item)
            save_workload(path, data)
            if args.json:
                print(json.dumps({"id": item["id"], "direction": second}))
            else:
                print(f"moved {args.ref} {second}")
            return 0

        if second == "to":
            if args.target is None:
                raise CLIError("`move <ref> to <target>` requires a target")
            path, data = load_workload_from_args(args)
            items = data["items"]
            found = find_by_ref(items, args.ref)
            if found is None:
                raise CLIError(f"item {args.ref} not found")
            item, source_parent, source_idx, _ = found

            target = args.target
            if not re.fullmatch(r"\d+(?:\.\d+)*", target):
                raise CLIError(f"move target must be a number reference, got {target!r}")
            parts = [int(p) for p in target.split(".")]
            if len(parts) == 1:
                target_parent_list = items
            else:
                parent_ref = ".".join(str(p) for p in parts[:-1])
                target_found = find_by_ref(items, parent_ref)
                if target_found is None:
                    raise CLIError(f"target parent {parent_ref} does not exist")
                target_parent_item = target_found[0]
                if _contains_subtree(item, target_parent_item["id"]):
                    raise CLIError(
                        f"cannot move {args.ref} to {target}: would create a cycle"
                    )
                target_parent_list = target_parent_item.setdefault("children", [])
            insert_idx = parts[-1] - 1

            source_parent.pop(source_idx)

            # `insert_idx` is the 0-based slot in the FINAL list. Same-parent moves
            # need no adjustment after the pop: e.g. `move 2.1 to 2.3` against
            # `[a, b, c]` pops a → `[b, c]`, then inserts a at index 2 → `[b, c, a]`,
            # leaving a at final position 3 as requested.

            # Out-of-range targets cap at end (siblings reflow).
            insert_idx = max(0, min(insert_idx, len(target_parent_list)))

            target_parent_list.insert(insert_idx, item)
            rollup(items)
            save_workload(path, data)
            if args.json:
                print(json.dumps({"id": item["id"], "target": target}))
            else:
                print(f"moved {args.ref} to {target}")
            return 0

        raise CLIError(
            f"expected one of up|down|top|bottom or 'to <target>', got {second!r}"
        )
