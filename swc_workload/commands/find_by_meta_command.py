"""`find-by-meta` — search items by `meta` content (presence + regex patterns)."""

from __future__ import annotations

import argparse
import json
import re

from ..cli_error import CLIError
from ..io import load_workload_from_args
from ..meta import parse_bool_flag, parse_path, read_at_path
from ..output import render_match_entry, render_match_line
from ..tree import iter_items
from .command import Command


class FindByMetaCommand(Command):
    name = "find-by-meta"
    help = "Search items by meta path (presence + optional regex on string values)."
    description = (
        "Search the workload for items whose `meta` contains a value at a "
        "dotted path. With no `<pattern>`, runs in presence mode — match any "
        "item where the path resolves to any value (including falsy values). "
        "With `<pattern>`, runs in regex mode — match items where the path "
        "resolves to a STRING value that `re.search(pattern, value)` matches; "
        "missing path / non-string leaf is a silent miss. "
        "`--meta true|false` includes each match's full meta blob (default false)."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "path",
            help=(
                "Dotted path inside each item's `meta`. `\"\"` (empty) refers "
                "to the root — matches every item that has a meta field."
            ),
        )
        parser.add_argument(
            "pattern",
            nargs="?",
            default=None,
            help=(
                "Optional regex pattern. When supplied, only items whose path "
                "resolves to a STRING value matching the regex are returned."
            ),
        )
        parser.add_argument(
            "--meta",
            dest="meta",
            default="false",
            metavar="true|false",
            help=(
                "Include each match's `meta` blob in the output (default: false)."
            ),
        )

    def execute(self, args) -> int:
        include_meta = parse_bool_flag(args.meta)

        # Compile the regex up front. Invalid regex → fail before any disk
        # work happens. Matches REQ-14.
        compiled: re.Pattern | None = None
        if args.pattern is not None:
            try:
                compiled = re.compile(args.pattern)
            except re.error as e:
                raise CLIError(
                    f"--pattern is not a valid regex: {e}"
                ) from e

        path_tuple = parse_path(args.path)

        _, data = load_workload_from_args(args)
        items = data["items"]

        matches: list[tuple[dict, tuple[int, ...]]] = []
        for item, _, _, number in iter_items(items):
            # Legacy items (no `meta` field) NEVER match — including empty path.
            # REQ-15 + solution.md decision.
            if "meta" not in item:
                continue
            meta_blob = item["meta"]
            # `read_at_path` only walks dicts — top-level meta must be a dict
            # (validated on load) but defensively skip non-dict shapes.
            if not isinstance(meta_blob, dict):
                continue

            found, value = read_at_path(meta_blob, path_tuple)
            if not found:
                continue
            if compiled is not None:
                # Pattern mode: leaf must be a string AND the regex must match.
                if not isinstance(value, str):
                    continue
                if not compiled.search(value):
                    continue
            matches.append((item, number))

        if args.json:
            out = []
            for item, number in matches:
                entry = render_match_entry(item, number)
                if include_meta:
                    entry["meta"] = item.get("meta", {})
                out.append(entry)
            print(json.dumps({"matches": out}))
        else:
            if not matches:
                print("no matches")
            else:
                for item, number in matches:
                    print(render_match_line(item, number))
        return 0
