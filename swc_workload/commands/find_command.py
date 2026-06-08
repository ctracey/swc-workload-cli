"""`find` — search work items by title, or by meta path (presence + pattern)."""

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


class FindCommand(Command):
    name = "find"
    help = "Find items by title pattern, or by meta path (presence + pattern)."
    description = """\
Find work items by title or meta content.

TITLE MODE (no --meta)
  Search items whose title contains <pattern> (case-insensitive substring).

    find plan                       # items with "plan" in the title
    find "phase 1"                  # multi-word

META PRESENCE MODE (--meta, no pattern)
  Match any item where the dotted path resolves to any value in meta,
  including falsy values (null, 0, false, "").

    find --meta tags                # items that have a `tags` key in meta
    find --meta ""                  # items that have any meta at all (empty path = root)
    find --meta swc.stage           # items where meta.swc.stage exists

META PATTERN MODE (--meta + pattern)
  <pattern> is a Python re.search() regex applied to the resolved value.

  String leaf — matched directly:
    find plan --meta swc.stage
    find "^plan$" --meta swc.stage

  Scalar leaf (number, bool, null) — coerced to JSON string ("1", "true", "null"):
    find 42 --meta count
    find true --meta active

  Array leaf — matches if the pattern hits any element, OR the whole array's
  JSON string (e.g. "[1, 2, 3]" with spaces after commas):
    find python --meta tags         # any element equals/contains "python"
    find "^python$" --meta tags     # element exactly "python"
    find "^\\[1, 2, 3\\]$" --meta nums  # exact array match

ARRAY INDEX TRAVERSAL
  Use bracket notation to index into arrays:
    find python --meta 'tags[0]'    # first tag is "python"
    find build --meta 'steps[0].name'
    find 1 --meta 'a[0]'            # first element equals 1 (numeric)

  Note: quote bracket paths in zsh to prevent glob expansion.

JSON output always includes the full `meta` blob for each match.
"""
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "pattern",
            nargs="?",
            default=None,
            help=(
                "In title mode: case-insensitive substring to match against "
                "item titles (required when --meta is not used). "
                "In meta mode: optional regex (re.search) matched against the "
                "value at --meta path. Omit for presence-only check."
            ),
        )
        parser.add_argument(
            "--meta",
            metavar="path",
            default=None,
            help=(
                "Dotted path inside each item's `meta`. Switches to meta mode. "
                "Empty string refers to the root (matches every item that has "
                "a meta field). Use bracket notation for array indices: "
                "tags[0], steps[0].name."
            ),
        )

    def execute(self, args) -> int:
        meta_path: str | None = args.meta
        pattern: str | None = args.pattern

        if meta_path is None and pattern is None:
            raise CLIError("pattern is required when --meta is not used")

        if meta_path is not None:
            return self._execute_meta(args, meta_path, pattern)
        else:
            return self._execute_title(args, pattern)

    def _execute_title(self, args, pattern: str) -> int:
        _, data = load_workload_from_args(args)
        items = data["items"]
        keyword = pattern.lower()
        matches: list[tuple[dict, tuple[int, ...]]] = []
        for item, _, _, number in iter_items(items):
            if keyword in item["title"].lower():
                matches.append((item, number))

        if args.json:
            out = [render_match_entry(item, number) for item, number in matches]
            print(json.dumps({"matches": out}))
        else:
            if not matches:
                print(f"no matches for {pattern!r}")
            else:
                for item, number in matches:
                    print(render_match_line(item, number))
        return 0

    def _execute_meta(self, args, meta_path: str, pattern: str | None) -> int:
        compiled: re.Pattern | None = None
        if pattern is not None:
            try:
                compiled = re.compile(pattern)
            except re.error as e:
                raise CLIError(f"pattern is not a valid regex: {e}") from e

        path_tuple = parse_path(meta_path)

        _, data = load_workload_from_args(args)
        items = data["items"]

        matches: list[tuple[dict, tuple[int, ...]]] = []
        for item, _, _, number in iter_items(items):
            if "meta" not in item:
                continue
            meta_blob = item["meta"]
            if not isinstance(meta_blob, dict):
                continue

            found, value = read_at_path(meta_blob, path_tuple)
            if not found:
                continue
            if compiled is not None:
                if isinstance(value, dict):
                    continue
                if isinstance(value, list):
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
