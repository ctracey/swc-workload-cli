"""Tier 1 — direct tests against `swc-workload --help` and subcommand help.

Invoked as `python -m swc_workload` (see conftest) so the test runs
against the package code regardless of whether the entry point has
been installed.
"""

from conftest import run_swc_workload


def _run(*args):
    return run_swc_workload(*args)


def test_top_level_help_lists_all_ops():
    result = _run("--help")
    assert result.returncode == 0
    out = result.stdout
    for op in ("init", "add", "delete", "list", "start", "complete", "reset", "exists"):
        assert op in out, f"top-level help missing {op!r}"
    # Should mention the required --workload flag.
    assert "--workload" in out or "swc workload" in out.lower()


def test_subcommand_help_describes_flags():
    result = _run("add", "--help")
    assert result.returncode == 0
    out = result.stdout
    assert "add" in out
    assert "to" in out and "at" in out
    assert "--workload" in out


def test_subcommand_help_works_without_workload_flag():
    """argparse short-circuits --help before requiring --workload, so
    `swc-workload list --help` exits 0 without needing a workload path.
    """
    result = _run("list", "--help")
    assert result.returncode == 0
    assert "--filter" in result.stdout
