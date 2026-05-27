"""Shared fixtures for swc-workload CLI tests.

Tests pass `--workload <tmp-path>` explicitly. The CLI is invoked as
`python -m swc_workload` so the argparse surface (and the exit code /
stderr behaviour) is covered end-to-end without depending on an
installed entry-point script. PYTHONPATH is set so the package resolves
whether or not `pip install -e .` has been run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(cmd: list[str], cwd: Path | None = None, env: dict | None = None):
    final_env = os.environ.copy()
    existing = final_env.get("PYTHONPATH", "")
    final_env["PYTHONPATH"] = (
        str(REPO_ROOT) + (os.pathsep + existing if existing else "")
    )
    if env:
        final_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=final_env,
        capture_output=True,
        text=True,
    )


def run_swc_workload(*args, workload: Path | None = None):
    """Invoke `python -m swc_workload` as a subprocess.

    `args` is the full arg list as passed on the command line — including
    `--workload` if the test wants to position it elsewhere. If `workload`
    is supplied, it is appended as `--workload <folder>` so most tests
    don't have to thread it through every call. The `--workload` contract
    is folder-path: swc-workload resolves <folder>/workload.json
    internally.
    """
    cmd = [sys.executable, "-m", "swc_workload", *map(str, args)]
    if workload is not None:
        cmd.extend(["--workload", str(workload)])
    return _run(cmd)


@pytest.fixture
def swcw(tmp_path):
    """Return (run_fn, workload_json_path).

    `run_fn(*args)` invokes swc-workload against the per-test workload
    folder (pytest's `tmp_path`). The returned `workload` value is the
    expected workload.json path inside that folder (for tests that need to
    read/write the file directly after init runs). The folder exists; the
    workload.json is NOT pre-initialised — each test calls `init` (or seeds
    the file) as needed.
    """
    folder = tmp_path
    workload_json = folder / "workload.json"

    def run(*args):
        return run_swc_workload(*args, workload=folder)

    return run, workload_json


@pytest.fixture
def swcw_ready(swcw):
    """Like `swcw` but with `init` pre-run so the workload exists."""
    run, workload = swcw
    result = run("init")
    assert result.returncode == 0, f"init failed: {result.stderr}"
    return run, workload
