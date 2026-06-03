"""`init` — create a fresh workload.json inside the supplied folder."""

from __future__ import annotations

import json
from typing import Optional

from ..cli_error import CLIError
from ..io import empty_workload, save_workload, workload_path_from_args
from .command import Command


class InitCommand(Command):
    name = "init"
    help = "Initialise a fresh workload tree."
    description = "Initialise a fresh, empty workload tree. Fails if one is already present."

    def get_epilog(self, *, hide_workload: bool) -> Optional[str]:
        if hide_workload:
            return None
        return (
            "Pure file-creation: writes workload.json inside the --workload "
            "folder. Does not touch .swc/_meta.json — the `swc workload` "
            "wrapper handles folder creation and branch registration."
        )

    def execute(self, args) -> int:
        """Pure file-creation: no branch awareness, no _meta.json registration.

        The `swc` layer is responsible for creating the folder and registering
        the branch→folder mapping before calling this op. We require the folder
        to already exist — `workload_path_from_args` enforces that.
        """
        path = workload_path_from_args(args)
        if path.exists():
            raise CLIError(f"workload already exists at {path}")
        save_workload(path, empty_workload())
        if args.json:
            print(json.dumps({"workload": str(path)}))
        else:
            print(f"initialised {path}")
        return 0
