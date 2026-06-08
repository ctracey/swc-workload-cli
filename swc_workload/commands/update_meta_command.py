"""`update-meta` — write a JSON value at a dotted path inside an item's meta."""

from __future__ import annotations

import argparse
import json

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..meta import parse_meta_object, parse_meta_value, parse_path, write_at_path
from ..tree import find_by_ref
from .command import Command


class UpdateMetaCommand(Command):
    name = "update-meta"
    help = "Write a JSON value at a dotted path inside an item's meta."
    description = """\
Write `<json-value>` at the dotted `<path>` inside the item's `meta`.
Replace-not-merge at every depth — writing a JSON object at a subtree
replaces the subtree wholly. Empty `<path>` replaces the whole `meta`
(value MUST be a JSON object). Missing intermediate objects are
created. An intermediate that exists but is not an object is rejected
to protect co-resident data.

EXAMPLES
  # String value
  update-meta 1 owner '"alice"'

  # Number value
  update-meta 1 priority '2'

  # Object value — replaces the whole subtree at that path
  update-meta 1 review '{"status": "approved", "by": "alice"}'

  # Nested path — creates intermediate objects as needed
  update-meta 1 swc.stage '"implement"'

  # Replace the whole meta root (empty path — value must be an object)
  update-meta 1 "" '{"owner": "alice", "priority": 1}'
"""
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)
        parser.add_argument(
            "path",
            help=(
                "Dotted path inside the item's `meta`. `\"\"` (empty string) "
                "refers to the root of `meta` — value MUST be a JSON object. "
                "`:` is a literal segment character (e.g. `swc:status.stage`)."
            ),
        )
        parser.add_argument(
            "value",
            metavar="json_value",
            help=(
                "JSON value to write at `<path>`. Any JSON type accepted at a "
                "non-empty path. Empty path requires a JSON object."
            ),
        )

    def execute(self, args) -> int:
        path_raw: str = args.path

        # Parse the value up front so a malformed value never causes a partial
        # write. Choice of parser depends on the path:
        # - empty path → object required (parse_meta_object with the
        #   `<json-value>` label so error messages name the positional the
        #   user actually typed — not the `--meta` flag from `add`).
        # - non-empty path → any JSON type (parse_meta_value).
        if path_raw == "":
            parsed_value = parse_meta_object(args.value, label="<json-value>")
        else:
            parsed_value = parse_meta_value(args.value)

        workload_path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, _, _, _ = found

        if path_raw == "":
            # Replace the whole meta with the parsed object.
            item["meta"] = parsed_value
        else:
            # Apply the leaf write into the existing meta dict, creating it
            # if the item is legacy (no `meta` field).
            meta = item.setdefault("meta", {})
            write_at_path(meta, parse_path(path_raw), parsed_value)

        save_workload(workload_path, data)

        if args.json:
            print(json.dumps({
                "id": item["id"],
                "path": path_raw,
                "value": parsed_value,
            }))
        else:
            display_path = path_raw if path_raw != "" else "<root>"
            print(f"[{item['id']}] meta {display_path} updated")
        return 0
