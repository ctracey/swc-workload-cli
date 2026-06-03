"""`delete` — drop a work item and all of its descendants."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..status import rollup
from ..tree import find_by_ref
from .command import Command


class DeleteCommand(Command):
    name = "delete"
    help = "Delete a work item (and its descendants)."
    description = (
        "Delete a work item and all of its descendants. Remaining siblings "
        "reflow numbers."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)

    def execute(self, args) -> int:
        path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        _, parent_list, idx, _ = found
        parent_list.pop(idx)
        rollup(items)
        save_workload(path, data)
        if args.json:
            print(json.dumps({"deleted": args.ref}))
        else:
            print(f"deleted {args.ref}")
        return 0
