"""Tier 1 — direct tests against `swc-workload --help` and subcommand help.

Invoked as `python -m swc_workload` (see conftest) so the test runs
against the package code regardless of whether the entry point has
been installed.
"""

from conftest import run_swc_workload

from swc_workload import __version__


def _run(*args):
    return run_swc_workload(*args)


def test_top_level_help_lists_all_ops():
    result = _run("--help")
    assert result.returncode == 0
    out = result.stdout
    for op in ("init", "add", "delete", "list", "update", "exists"):
        assert op in out, f"top-level help missing {op!r}"
    # Should mention the required --workload flag.
    assert "--workload" in out or "swc workload" in out.lower()


def test_top_level_help_shows_version():
    result = _run("--help")
    assert result.returncode == 0
    assert __version__ in result.stdout, (
        f"top-level --help should show version {__version__!r}"
    )


def test_short_version_flag():
    result = _run("-v")
    assert result.returncode == 0
    assert __version__ in result.stdout, (
        f"`-v` should print version {__version__!r}, got {result.stdout!r}"
    )


def test_long_version_flag():
    result = _run("--version")
    assert result.returncode == 0
    assert __version__ in result.stdout, (
        f"`--version` should print version {__version__!r}, got {result.stdout!r}"
    )


def test_version_flag_outputs_bare_pinned_string():
    """Pin the exact stripped output to the literal `1.2.0` — not via
    `__version__` — so a regression on either the version bump or the
    bare-format (no `swc workload ` prefix) is caught. Per
    cli-change-spec.md, the MCP shells out to `swc-workload --version`
    and reads stdout directly.
    """
    long_form = _run("--version")
    assert long_form.returncode == 0
    assert long_form.stdout.strip() == "1.2.0", (
        f"`--version` must emit bare `1.2.0`, got {long_form.stdout!r}"
    )

    short_form = _run("-v")
    assert short_form.returncode == 0
    assert short_form.stdout.strip() == "1.2.0", (
        f"`-v` must emit bare `1.2.0`, got {short_form.stdout!r}"
    )


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
