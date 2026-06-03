"""`complete` — set status to done. Warns on stderr if children aren't all done."""

from __future__ import annotations

import argparse

from ..status import STATUS_DONE
from .command import Command, run_status_transition


class CompleteCommand(Command):
    name = "complete"
    help = "Mark a work item as done."
    description = (
        "Set the work item's status to done. Parent ancestors re-roll. "
        "If the item has children that are not all done, a warning is "
        "emitted to stderr but the change is accepted."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)

    def execute(self, args) -> int:
        return run_status_transition(args, STATUS_DONE)
