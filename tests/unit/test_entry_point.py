"""Smoke test for the `swc-workload` console-script entry point.

Verifies that `pyproject.toml` wiring is correct end-to-end: after
`pip install -e .`, `importlib.metadata` should report a console_scripts
entry named `swc-workload` pointing at `swc_workload.cli:main`, and that
target should be importable and callable.

If this test fails with "entry point not registered", run:

    pip install -e .

from the repo root.
"""

from __future__ import annotations

import importlib.metadata as md
import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _swc_workload_entry_point():
    try:
        eps = md.entry_points(group="console_scripts")
    except TypeError:
        eps = md.entry_points().get("console_scripts", [])
    matches = [ep for ep in eps if ep.name == "swc-workload"]
    if not matches:
        pytest.fail(
            "`swc-workload` console-script entry point not registered. "
            "Run `pip install -e .` from the repo root."
        )
    return matches[0]


def test_entry_point_is_registered():
    ep = _swc_workload_entry_point()
    assert ep.value == "swc_workload.cli:main", (
        f"entry point points at {ep.value!r}, expected 'swc_workload.cli:main'"
    )


def test_entry_point_target_is_callable():
    ep = _swc_workload_entry_point()
    target = ep.load()
    assert callable(target), "entry point target is not callable"


def test_entry_point_resolves_to_local_source():
    """Guard against a stale global/pipx install shadowing the local code.

    With `pip install -e .` in an active venv, the entry point's target
    is the same file as `swc_workload/cli.py` in this repo. If a
    different copy is being resolved, the editable install isn't active
    in the current environment.
    """
    ep = _swc_workload_entry_point()
    target = ep.load()
    target_file = Path(inspect.getfile(target)).resolve()
    assert REPO_ROOT in target_file.parents, (
        f"entry point resolved to {target_file}, which is outside the repo "
        f"at {REPO_ROOT}. Activate a venv and run `pip install -e .`."
    )
