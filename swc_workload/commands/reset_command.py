"""`reset` — set status to not-started. Re-opens done items (explicit verb)."""

from __future__ import annotations

import argparse

from ..status import STATUS_NOT_STARTED
from .command import Command, run_status_transition


class ResetCommand(Command):
    name = "reset"
    help = "Mark a work item as not-started (re-opens done items too)."
    description = (
        "Set the work item's status to not-started. Parent ancestors re-roll. "
        "`reset` is an explicit verb — it WILL re-open a done item, unlike "
        "`start`, which preserves done."
    )

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("ref", help=self.ref_help)

    def execute(self, args) -> int:
        return run_status_transition(args, STATUS_NOT_STARTED, allow_downgrade=True)
