"""swc-workload — pure tree manager for workload.json.

Path-driven: takes `--workload <folder>` on every op. The folder must
contain (or, for `init`, will contain) a `workload.json` file — the file
name is convention-locked. Knows nothing about git branches,
`.swc/_meta.json`, or context resolution. The user-facing
`swc workload <op>` command (in `bin/swc`) resolves the folder and
forwards the op here.

Invocation:
    python3 bin/swc-workload <op> --workload <folder> [args]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from . import __version__
from .commands import ALL as REGISTERED_COMMANDS
from .cli_error import CLIError


def build_parser() -> argparse.ArgumentParser:
    hide_workload = os.environ.get("SWC_HIDE_WORKLOAD_ARG") == "1"

    p = argparse.ArgumentParser(
        prog="swc workload",
        description=f"Manage the workload tree — work items, status, ordering. (version {__version__})",
        epilog=None if hide_workload else (
            "Folder contract: every op operates on workload.json inside the "
            "folder passed via --workload. The folder must already exist. For "
            "branch-aware context resolution, use the `swc workload <op>` "
            "wrapper, which resolves the folder from the current branch and "
            "forwards the op here."
        ),
    )
    p.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__version__}",
    )

    sub = p.add_subparsers(dest="op", required=True, metavar="<op>")

    for command in REGISTERED_COMMANDS:
        command.register(sub, hide_workload=hide_workload)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CLIError as e:
        sys.stderr.write(f"{e}\n")
        return e.exit_code
    except OSError as e:
        # File-system errors (permission denied, disk full, etc.) should not
        # surface as raw Python tracebacks. Real bugs (anything not OSError /
        # CLIError) are deliberately left uncaught so development surfaces them.
        sys.stderr.write(f"file system error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
