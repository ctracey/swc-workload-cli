"""`summary` — emit total / done / wip counts and a progress percentage."""

from __future__ import annotations

import json

from ..io import load_workload_from_args
from ..status import STATUS_DONE, STATUS_IN_PROGRESS
from ..tree import iter_items
from .command import Command


class SummaryCommand(Command):
    name = "summary"
    help = "Emit total / done / progress percentage."
    description = "Emit total count, done count, and progress percentage for the workload."

    def execute(self, args) -> int:
        path, data = load_workload_from_args(args)
        items = data["items"]
        total = 0
        done = 0
        wip = 0
        for item, _, _, _ in iter_items(items):
            total += 1
            if item["status"] == STATUS_DONE:
                done += 1
            elif item["status"] == STATUS_IN_PROGRESS:
                wip += 1
        pct = int(round((done / total) * 100)) if total else 0
        if args.json:
            print(json.dumps({"total": total, "done": done, "wip": wip, "progress": pct}))
        else:
            print(f"total={total} done={done} wip={wip} progress={pct}%")
        return 0
