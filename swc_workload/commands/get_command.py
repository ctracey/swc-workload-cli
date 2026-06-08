"""`get` — return a single work item by ref, always including meta in JSON output."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..io import load_workload_from_args
from ..output import render_item_json, render_item_text
from ..tree import find_by_ref
from .command import Command


class GetCommand(Command):
    name = "get"
    help = "Return a single work item by ref."
    description = (
        "Return a single work item resolved by ref (number or hash). "
        "Output is a single JSON object (NOT wrapped in `{items: [...]}`) "
        "when --json is supplied. The `meta` field is always included in "
        "JSON output (legacy items without a meta field project `meta: {}`)."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)

    def execute(self, args) -> int:
        path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, _, _, number = found

        if args.json:
            print(json.dumps(render_item_json(item, number)))
        else:
            print(render_item_text(item, number, show_ids=True))
        return 0
