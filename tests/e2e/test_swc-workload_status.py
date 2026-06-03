"""Tier 1 — direct tests against `bin/swc-workload --workload <tmp-path>`.

Status updates, rollup, downgrade-guard, and the parent-marked-done warning
path. These are the highest-risk behaviours per solution.md, so they're
covered directly without the indirection of branch resolution.
"""

import json


# ---------------------------------------------------------------------------
# REQ-12 — status update and rollup
# ---------------------------------------------------------------------------


def test_marking_child_in_progress_rolls_parent_to_in_progress(swcw_ready):
    run, workload = swcw_ready
    run("add", "one")
    run("add", "two")
    run("add", "three")
    run("add", "3a", "to", "3")
    run("add", "3b", "to", "3")

    result = run("start", "3.2")
    assert result.returncode == 0, result.stderr

    after = json.loads(run("list", "--json").stdout)["items"]
    parent = after[2]
    assert parent["children"][1]["status"] == "in-progress"
    assert parent["status"] == "in-progress"


def test_marking_last_child_done_rolls_parent_to_done(swcw_ready):
    run, workload = swcw_ready
    run("add", "p")
    run("add", "a", "to", "1")
    run("add", "b", "to", "1")

    run("complete", "1.1")
    run("start", "1.2")
    result = run("complete", "1.2")
    assert result.returncode == 0, result.stderr

    after = json.loads(run("list", "--json").stdout)["items"]
    p = after[0]
    assert p["children"][1]["status"] == "done"
    assert p["status"] == "done"


# ---------------------------------------------------------------------------
# REQ-13 — done is sticky
# ---------------------------------------------------------------------------


def test_start_on_done_is_sticky_and_leaves_file_unchanged(swcw_ready):
    """`start` on a done item is silently preserved — file unchanged, exit 0.
    Done-sticky still applies to `start`; `reset` is the explicit re-open verb."""
    run, workload = swcw_ready
    run("add", "leaf")
    run("complete", "1")

    original = workload.read_text()
    result = run("start", "1")
    assert result.returncode == 0, result.stderr

    assert workload.read_text() == original

    after = json.loads(run("list", "--json").stdout)["items"]
    assert after[0]["status"] == "done"


def test_reset_on_done_re_opens_it(swcw_ready):
    """`reset` is an explicit verb and DOES re-open a done item.

    This is the deliberate exception to the done-sticky rule that applies to
    `start`: `reset` is unambiguous user intent to re-open.
    """
    run, workload = swcw_ready
    run("add", "leaf")
    run("complete", "1")
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "done"

    result = run("reset", "1")
    assert result.returncode == 0, result.stderr

    after = json.loads(run("list", "--json").stdout)["items"]
    assert after[0]["status"] == "not-started"


# ---------------------------------------------------------------------------
# Pre-refactor safety net — `--json` output for status-transition commands.
# `_add_common()` advertises `--json` on every subcommand but coverage existed
# only for read ops. Pin the current shapes for `start`, `complete`, `reset`
# so the refactor cannot silently regress structured output.
# ---------------------------------------------------------------------------


def test_start_json_emits_id_and_new_status(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("start", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["status"] == "in-progress"


def test_complete_json_emits_id_and_new_status(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("complete", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["status"] == "done"


def test_reset_json_emits_id_and_new_status(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    run("complete", "1")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("reset", "1", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["status"] == "not-started"


# ---------------------------------------------------------------------------
# F-03 (a) — parent marked done with undone children warns on stderr
# ---------------------------------------------------------------------------


def test_parent_marked_done_with_undone_children_warns_on_stderr(swcw_ready):
    run, workload = swcw_ready
    run("add", "p")
    run("add", "a", "to", "1")
    run("add", "b", "to", "1")
    run("add", "c", "to", "1")

    run("complete", "1.1")
    before = workload.read_text()

    result = run("complete", "1")
    assert result.returncode == 0, result.stderr
    msg = result.stderr.lower()
    assert "warning" in msg
    assert "1" in result.stderr
    assert "done" in msg
    assert workload.read_text() != before
    after = json.loads(run("list", "--json").stdout)["items"]
    assert after[0]["status"] == "done"
