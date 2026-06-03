"""`start` — set status to in-progress. Silently preserved if item is already done."""

from __future__ import annotations

import argparse

from ..status import STATUS_IN_PROGRESS
from .command import Command, run_status_transition


class StartCommand(Command):
    name = "start"
    help = "Mark a work item as in-progress."
    description = (
        "Set the work item's status to in-progress. Parent ancestors re-roll. "
        "A done item is silently preserved (file unchanged, exits 0)."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)

    def execute(self, args) -> int:
        return run_status_transition(args, STATUS_IN_PROGRESS)
