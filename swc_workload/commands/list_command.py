"""`list` — render the workload tree, optionally scoped to a single item's subtree."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..filters import apply_filters, parse_filter
from ..io import load_workload_from_args
from ..output import render_item_json, render_item_text, render_text, to_json_tree
from ..tree import find_by_ref
from .command import Command


class ListCommand(Command):
    name = "list"
    help = "Display workload tree (optional ref to scope to a subtree; --filter/--exclude supported)."
    description = (
        "Display the workload tree with status symbols.\n"
        "\n"
        "Forms:\n"
        "  list                       — full tree.\n"
        "  list <ref>                 — that item plus its descendants.\n"
        "\n"
        "Filters:\n"
        "  --filter key:val[,val…]    — include items matching the filter; repeatable.\n"
        "  --exclude key:val[,val…]   — exclude items matching the filter.\n"
        "  Supported keys: status. Filters apply to either form; with a ref they\n"
        "  scope to the subtree (a parent is kept when any descendant matches)."
    )
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "ref",
            nargs="?",
            default=None,
            help="Optional item reference (number or hash). When given, render just that item and its descendants.",
        )
        parser.add_argument(
            "--filter",
            action="append",
            help="Include filter — key:val[,val…]. Supported keys: status. Repeatable.",
        )
        parser.add_argument(
            "--exclude",
            dest="exclude",
            action="append",
            help="Exclude filter — same syntax and supported keys as --filter.",
        )
        parser.add_argument(
            "--no-ids",
            dest="show_ids",
            action="store_false",
            default=True,
            help="Hide hash IDs from output (IDs are shown by default).",
        )

    def execute(self, args) -> int:
        """Filters (--filter / --exclude) apply to either form. With `ref`, the
        filters are applied to the subtree rooted at the ref'd item. apply_filters
        keeps a parent when any descendant matches (and drops non-matching
        descendants), so the ref'd item is visible whenever something inside it
        matches.
        """
        path, data = load_workload_from_args(args)
        items = data["items"]

        filters = [parse_filter(f) for f in (args.filter or [])]
        excludes = [parse_filter(f) for f in (args.exclude or [])]

        if args.ref:
            found = find_by_ref(items, args.ref)
            if found is None:
                raise CLIError(f"item {args.ref} not found")
            item, _, _, number = found
            filtered = apply_filters([(item, number)], filters, excludes)
            if args.json:
                out = [render_item_json(n, number) for n in filtered]
                print(json.dumps({"items": out}))
            else:
                print("\n".join(render_item_text(n, number, show_ids=args.show_ids) for n in filtered))
            return 0

        top_pairs = [(item, (i + 1,)) for i, item in enumerate(items)]
        filtered = apply_filters(top_pairs, filters, excludes)
        if args.json:
            print(json.dumps({"items": to_json_tree(filtered)}))
        else:
            print(render_text(filtered, show_ids=args.show_ids))
        return 0
