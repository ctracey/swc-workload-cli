"""`update` — update a field on a work item: title, status, or meta path."""

from __future__ import annotations

import argparse
import json
import sys

from ..cli_error import CLIError
from ..io import load_workload_from_args, save_workload
from ..meta import parse_meta_object, parse_path, write_at_path
from ..status import STATUS_ALIASES, apply_status_transition
from ..tree import check_no_sibling_title_collision, find_by_ref
from ..validation import validate_title
from .command import Command

_PROTECTED = {"id", "number"}
_SUPPORTED = "title, status, meta, or meta.<dotted-path>"


def _parse_meta_value(raw: str):
    """Parse ``raw`` as JSON; fall back to a plain string on parse failure.

    This lets callers omit shell quoting for string values:
    ``update 1 meta.stage plan`` stores the string ``"plan"``.
    Typed JSON (numbers, booleans, arrays, objects) still works as-is.
    To store the string ``"true"`` rather than the boolean, quote it:
    ``'"true"'``.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


class UpdateCommand(Command):
    name = "update"
    help = "Update a field on a work item — title, status, or meta path."
    description = """\
Update a field on a work item. The `<path>` determines what is changed
and how `<value>` is interpreted.

TITLE
  Plain string — same validation as adding a new item.

    update 1 title "Refactor auth module"

STATUS
  Plain string — aliases accepted (e.g. todo, wip, complete).
  Valid canonical values: not-started, in-progress, done.
  Parent status is re-derived from children after the change.

    update 1 status in-progress
    update 2 status done
    update 3 status todo          # alias for not-started

META ROOT  (path = "meta")
  Replace the entire meta object. Value MUST be a JSON object.

    update 1 meta '{"owner":"alice","priority":1}'
    update 1 meta '{}'            # clear all meta

META SUBPATH  (path = "meta.<dotted-path>")
  Write a value at the dotted path inside the item's meta.
  Replace-not-merge — writing an object at a subtree replaces it wholly.
  Missing intermediate objects are created automatically.
  Array index traversal uses bracket notation.

  Value is parsed as JSON first. If that fails, the raw text is stored
  as a string — so plain words work without shell quoting:

    update 1 meta.owner alice            # stores string "alice"
    update 1 meta.stage implement        # stores string "implement"
    update 1 meta.priority 2             # stores number 2 (valid JSON)
    update 1 meta.active true            # stores boolean true (valid JSON)
    update 1 meta.review '{"status":"approved","by":"alice"}'
    update 1 meta.swc:status.stage plan
    update 1 'meta.tags[0]' python       # write first element
    update 1 'meta.steps[0].name' build  # nested array index

  To store the string "true" rather than the boolean, use JSON quoting:
    update 1 meta.flag '"true"'

  Note: bracket paths must be quoted in zsh to prevent glob expansion.

RESTRICTIONS
  id and number cannot be updated.
  Any other top-level field is rejected with an error.
"""
    formatter_class = argparse.RawDescriptionHelpFormatter

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)
        parser.add_argument(
            "path",
            help=(
                "Field to update: `title`, `status`, `meta` (root replacement), "
                "or `meta.<dotted-path>` (e.g. meta.owner, meta.tags[0]). "
                "`id` and `number` are rejected."
            ),
        )
        parser.add_argument(
            "value",
            help=(
                "New value. For `title` and `status`: plain string. "
                "For `meta`: JSON object. "
                "For `meta.*`: JSON value, or plain text (stored as a string "
                "when JSON parsing fails)."
            ),
        )

    def execute(self, args) -> int:
        path: str = args.path

        if path in _PROTECTED:
            raise CLIError(f"'{path}' cannot be updated")

        if path == "title":
            return self._update_title(args)
        if path == "status":
            return self._update_status(args)
        if path == "meta":
            return self._update_meta_root(args)
        if path.startswith("meta."):
            return self._update_meta_subpath(args, path[len("meta."):])

        raise CLIError(
            f"unknown field '{path}': supported paths are {_SUPPORTED}"
        )

    def _update_title(self, args) -> int:
        new_title: str = args.value
        validate_title(new_title)
        workload_path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, parent_list, _, _ = found
        check_no_sibling_title_collision(new_title, parent_list, exclude_id=item["id"])
        item["title"] = new_title
        save_workload(workload_path, data)
        if args.json:
            print(json.dumps({"id": item["id"], "path": "title", "value": new_title}))
        else:
            print(f"updated [{item['id']}] title -> {new_title}")
        return 0

    def _update_status(self, args) -> int:
        raw: str = args.value
        canonical = STATUS_ALIASES.get(raw.lower())
        if canonical is None:
            valid = sorted(set(STATUS_ALIASES.values()))
            raise CLIError(
                f"invalid status {raw!r}: must be one of {', '.join(valid)}"
            )
        workload_path, data = load_workload_from_args(args)
        items = data["items"]
        item, _, warning = apply_status_transition(
            items, args.ref, canonical, allow_downgrade=True
        )
        if warning:
            print(warning, file=sys.stderr)
        save_workload(workload_path, data)
        if args.json:
            print(json.dumps({"id": item["id"], "path": "status", "value": item["status"]}))
        else:
            print(f"updated [{item['id']}] status -> {item['status']}")
        return 0

    def _update_meta_root(self, args) -> int:
        parsed = parse_meta_object(args.value, label="<value>")
        workload_path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, _, _, _ = found
        item["meta"] = parsed
        save_workload(workload_path, data)
        if args.json:
            print(json.dumps({"id": item["id"], "path": "meta", "value": parsed}))
        else:
            print(f"updated [{item['id']}] meta")
        return 0

    def _update_meta_subpath(self, args, subpath: str) -> int:
        parsed = _parse_meta_value(args.value)
        workload_path, data = load_workload_from_args(args)
        items = data["items"]
        found = find_by_ref(items, args.ref)
        if found is None:
            raise CLIError(f"item {args.ref} not found")
        item, _, _, _ = found
        meta = item.setdefault("meta", {})
        write_at_path(meta, parse_path(subpath), parsed)
        save_workload(workload_path, data)
        full_path = f"meta.{subpath}"
        if args.json:
            print(json.dumps({"id": item["id"], "path": full_path, "value": parsed}))
        else:
            print(f"updated [{item['id']}] {full_path}")
        return 0
