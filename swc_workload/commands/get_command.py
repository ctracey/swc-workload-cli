"""`get` — return a single work item by ref, optionally including its meta."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..io import load_workload_from_args
from ..meta import parse_bool_flag
from ..output import render_item_json, render_item_text
from ..tree import find_by_ref
from .command import Command


class GetCommand(Command):
    name = "get"
    help = "Return a single work item by ref (includes meta by default)."
    description = (
        "Return a single work item resolved by ref (number or hash). "
        "Output is a single JSON object (NOT wrapped in `{items: [...]}`) "
        "when --json is supplied. `--meta true|false` controls whether the "
        "item's `meta` blob is included; default is `true`."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)
        parser.add_argument(
            "--meta",
            dest="meta",
            default="true",
            metavar="true|false",
            help=(
                "Include the item's `meta` blob in the output (default: true). "
                "Use `--meta false` to omit the `meta` key."
            ),
        )

    def execute(self, args) -> int:
        include_meta = parse_bool_flag(args.meta)

        path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, _, _, number = found

        if args.json:
            payload = render_item_json(item, number)
            if include_meta:
                # Project meta: {} for legacy items missing the field.
                # The on-disk file is NOT rewritten — REQ-15.
                payload["meta"] = item.get("meta", {})
            print(json.dumps(payload))
        else:
            print(render_item_text(item, number, show_ids=True))
        return 0
