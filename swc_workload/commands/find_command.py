"""`find` — search work items by case-insensitive substring match on title."""

from __future__ import annotations

import argparse
import json

from ..io import load_workload_from_args
from ..output import render_match_entry, render_match_line
from ..tree import iter_items
from .command import Command


class FindCommand(Command):
    name = "find"
    help = "Find items by keyword in title."
    description = (
        "Find work items whose title contains the given keyword "
        "(case-insensitive substring match). Returns all matches; the "
        "caller decides what to do with multiple hits."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "keyword",
            help="Substring to match against item titles (case-insensitive).",
        )

    def execute(self, args) -> int:
        path, data = load_workload_from_args(args)
        items = data["items"]
        keyword = args.keyword.lower()
        matches: list[tuple[dict, tuple[int, ...]]] = []
        for item, _, _, number in iter_items(items):
            if keyword in item["title"].lower():
                matches.append((item, number))

        if args.json:
            out = [render_match_entry(item, number) for item, number in matches]
            print(json.dumps({"matches": out}))
        else:
            if not matches:
                print(f"no matches for {args.keyword!r}")
            else:
                for item, number in matches:
                    print(render_match_line(item, number))
        return 0
