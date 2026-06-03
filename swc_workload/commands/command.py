"""Base class for CLI subcommand classes."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from ..io import load_workload_from_args, save_workload
from ..status import STATUS_DONE, apply_status_transition


class Command:
    """A CLI subcommand.

    Subclasses declare `name`, `help`, and optionally `description` /
    `formatter_class` as class attributes. They override `add_arguments()` to
    attach positional/option arguments to their subparser, and `execute()` to
    run the command. The base `register()` handles the shared scaffolding —
    subparser creation, `--workload` / `--json` flags via `add_common()`, and
    wiring `args.func` to `execute()`. Override `get_epilog()` for
    `hide_workload`-aware epilogs.
    """

    name: str = ""
    help: str = ""
    description: Optional[str] = None
    formatter_class: type = argparse.HelpFormatter

    # Shared help text for the `ref` positional used by rename, delete, move,
    # reset, start, complete. Subclasses that need it reference `self.ref_help`.
    ref_help: str = "Work item reference — number (e.g. `2.3`) or 7-char hash ID."

    def register(
        self,
        subparsers: argparse._SubParsersAction,
        *,
        hide_workload: bool = False,
    ) -> argparse.ArgumentParser:
        p = subparsers.add_parser(
            self.name,
            help=self.help,
            description=self.description,
            epilog=self.get_epilog(hide_workload=hide_workload),
            formatter_class=self.formatter_class,
        )
        add_common(p, hide_workload=hide_workload)
        self.add_arguments(p)
        p.set_defaults(func=self.execute)
        return p

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Override to add positional/option arguments. Default: no extra args."""

    def get_epilog(self, *, hide_workload: bool) -> Optional[str]:
        """Override to return a subparser epilog. Default: none."""
        return None

    def execute(self, args) -> int:
        raise NotImplementedError


def add_common(parser: argparse.ArgumentParser, *, hide_workload: bool) -> None:
    """Common flags accepted on every subcommand.

    `hide_workload` removes `--workload` from rendered help (usage line + options
    block) while leaving it functionally required for parsing — the `swc`
    wrapper sets `SWC_HIDE_WORKLOAD_ARG=1` so porcelain users don't see a flag
    they never supply.
    """
    workload_help = (
        argparse.SUPPRESS
        if hide_workload
        else "Path to the workload folder (containing workload.json)."
    )
    parser.add_argument(
        "--workload",
        required=True,
        help=workload_help,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output.",
    )


def run_status_transition(
    args,
    new_status: str,
    *,
    allow_downgrade: bool = False,
) -> int:
    """Load, apply a status transition, save, and emit output.

    Shared I/O orchestration used by `reset`, `start`, `complete`. Calls into
    the pure `apply_status_transition` in status.py for the actual mutation.
    """
    path, data = load_workload_from_args(args)
    items = data["items"]
    item, preserved, warning = apply_status_transition(
        items, args.ref, new_status, allow_downgrade=allow_downgrade,
    )

    if preserved:
        # Done-sticky kicked in: no file write, no error, exit 0.
        if args.json:
            print(json.dumps({"id": item["id"], "status": STATUS_DONE, "preserved": True}))
        else:
            print(f"[{item['id']}] preserved as done")
        return 0

    if warning:
        sys.stderr.write(warning + "\n")

    save_workload(path, data)
    if args.json:
        print(json.dumps({"id": item["id"], "status": new_status}))
    else:
        print(f"[{item['id']}] -> {new_status}")
    return 0
