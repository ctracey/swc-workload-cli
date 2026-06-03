"""`exists` — lenient file-presence check for workload.json inside --workload."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .command import Command


class ExistsCommand(Command):
    name = "exists"
    help = "Check whether a workload is initialised."
    description = (
        "Check whether a workload is initialised. Lenient: returns false "
        "(never errors) for missing folders, wrong-type paths, or missing "
        "workload.json, so callers can probe non-destructively."
    )

    def get_epilog(self, *, hide_workload: bool) -> Optional[str]:
        if hide_workload:
            return None
        return (
            "Unique among swc-workload ops: does NOT enforce the strict folder "
            "contract — every other op errors if --workload is missing or not "
            "a directory."
        )

    def execute(self, args) -> int:
        """Lenient: every "no" case returns false with exit 0, nothing on stderr.

        Cases:
          * folder missing                       → false
          * path is a file, not a directory      → false
          * folder exists, no workload.json      → false
          * folder exists, workload.json present → true
        """
        folder = Path(args.workload) if args.workload else None
        present = bool(
            folder is not None
            and folder.is_dir()
            and (folder / "workload.json").is_file()
        )
        if args.json:
            print(json.dumps({"exists": present}))
        else:
            print("true" if present else "false")
        return 0
