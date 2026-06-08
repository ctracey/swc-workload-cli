"""`find-by-meta` — search items by `meta` content (presence + regex patterns)."""

from __future__ import annotations

import argparse
import json
import re

from ..cli_error import CLIError
from ..io import load_workload_from_args
from ..meta import parse_path, read_at_path
from ..output import render_match_entry, render_match_line
from ..tree import iter_items
from .command import Command


class FindByMetaCommand(Command):
    name = "find-by-meta"
    help = "Search items by meta path (presence + optional regex on string values)."
    description = """\
Search the workload for items whose `meta` contains a value at a dotted path.

PRESENCE MODE (no pattern)
  Match any item where the path resolves to any value, including falsy ones.

  # Items that have a `tags` key in meta
  find-by-meta tags

  # Items that have any meta at all (empty path = root)
  find-by-meta ""

  # Items where meta.swc.stage exists
  find-by-meta swc.stage

PATTERN MODE (with pattern)
  Pattern is a Python re.search() regex applied to the resolved value.

  String leaf — matched directly:
    find-by-meta swc.stage plan
    find-by-meta swc.stage "^plan$"

  Scalar leaf (number, bool, null) — coerced to JSON string ("1", "true", "null"):
    find-by-meta count 42
    find-by-meta active true

  Array leaf — matches if the pattern hits any element, OR the whole array's
  JSON string (e.g. "[1, 2, 3]" with spaces after commas):
    find-by-meta tags python          # any element equals/contains "python"
    find-by-meta tags "^python$"      # element exactly "python"
    find-by-meta nums "^\\[1, 2, 3\\]$"  # exact array match

ARRAY INDEX TRAVERSAL
  Use bracket notation to index into arrays:
    find-by-meta 'tags[0]' python     # first tag is "python"
    find-by-meta 'steps[0].name' build
    find-by-meta 'a[0]' 1             # first element equals 1 (numeric)

  Note: quote bracket paths in zsh to prevent glob expansion.

JSON output always includes the full `meta` blob for each match.
"""
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "path",
            help=(
                "Dotted path inside each item's `meta`. Empty string refers to "
                "the root (matches every item with a meta field). Use bracket "
                "notation for array indices: tags[0], steps[0].name."
            ),
        )
        parser.add_argument(
            "pattern",
            nargs="?",
            default=None,
            help=(
                "Optional regex (re.search). Matches string values directly, "
                "scalars via JSON string coercion, and arrays by element or "
                "whole-array JSON string."
            ),
        )

    def execute(self, args) -> int:
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
                # Pattern mode: match against string representation of the
                # resolved value. Objects (dicts) are always a miss — they
                # are traversed via path, not matched directly.
                if isinstance(value, dict):
                    continue
                if isinstance(value, list):
                    # Match if the whole array's JSON string matches, OR any
                    # individual non-object element's string form matches.
                    json_array = json.dumps(value)
                    element_hit = any(
                        not isinstance(el, dict)
                        and compiled.search(
                            el if isinstance(el, str) else json.dumps(el)
                        )
                        for el in value
                    )
                    if not (compiled.search(json_array) or element_hit):
                        continue
                else:
                    # String leaf matches directly; scalars (int, float, bool,
                    # None) are coerced to their JSON string form ("1", "true",
                    # "null") so patterns can match them.
                    coerced = value if isinstance(value, str) else json.dumps(value)
                    if not compiled.search(coerced):
                        continue
            matches.append((item, number))

        if args.json:
            out = [render_match_entry(item, number) for item, number in matches]
            print(json.dumps({"matches": out}))
        else:
            if not matches:
                print("no matches")
            else:
                for item, number in matches:
                    print(render_match_line(item, number))
        return 0
