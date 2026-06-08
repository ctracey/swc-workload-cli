"""`update` — update a work item's title; preserves id, status, parent, and position."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..tree import check_no_sibling_title_collision, find_by_ref
from ..validation import validate_title
from .command import Command


class UpdateCommand(Command):
    name = "update"
    help = "Update a work item's title."
    description = (
        "Update a work item's title. The hash ID, status, parent, and position are "
        "preserved. Titles must not start with a number-prefix pattern."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)
        parser.add_argument(
            "title",
            help="New title. Must not start with a number-prefix pattern.",
        )

    def execute(self, args) -> int:
        validate_title(args.title)
        path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, parent_list, _, _ = found
        check_no_sibling_title_collision(args.title, parent_list, exclude_id=item["id"])
        item["title"] = args.title
        save_workload(path, data)
        if args.json:
            print(json.dumps({"id": item["id"], "title": args.title}))
        else:
            print(f"updated [{item['id']}] -> {args.title}")
        return 0
