"""Tier 1 — status transitions via `update <ref> status <value>`.

Status updates, rollup, and the parent-marked-done warning path.
These are the highest-risk behaviours per solution.md.
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

    result = run("update", "3.2", "status", "in-progress")
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

    run("update", "1.1", "status", "done")
    run("update", "1.2", "status", "in-progress")
    result = run("update", "1.2", "status", "done")
    assert result.returncode == 0, result.stderr

    after = json.loads(run("list", "--json").stdout)["items"]
    p = after[0]
    assert p["children"][1]["status"] == "done"
    assert p["status"] == "done"


# ---------------------------------------------------------------------------
# Explicit status update always honours the requested value (no done-sticky)
# ---------------------------------------------------------------------------


def test_update_status_on_done_item_changes_it(swcw_ready):
    """`update status` always applies — there is no done-sticky guard."""
    run, workload = swcw_ready
    run("add", "leaf")
    run("update", "1", "status", "done")
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "done"

    result = run("update", "1", "status", "in-progress")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "in-progress"


def test_update_status_not_started_re_opens_done_item(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    run("update", "1", "status", "done")
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "done"

    result = run("update", "1", "status", "not-started")
    assert result.returncode == 0, result.stderr
    assert json.loads(run("list", "--json").stdout)["items"][0]["status"] == "not-started"


# ---------------------------------------------------------------------------
# JSON output shape — {id, path, value}
# ---------------------------------------------------------------------------


def test_update_status_in_progress_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("update", "1", "status", "in-progress", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["path"] == "status"
    assert payload["value"] == "in-progress"


def test_update_status_done_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("update", "1", "status", "done", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["path"] == "status"
    assert payload["value"] == "done"


def test_update_status_not_started_json_output(swcw_ready):
    run, workload = swcw_ready
    run("add", "leaf")
    run("update", "1", "status", "done")
    target_id = json.loads(run("list", "--json").stdout)["items"][0]["id"]

    result = run("update", "1", "status", "not-started", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["id"] == target_id
    assert payload["path"] == "status"
    assert payload["value"] == "not-started"


# ---------------------------------------------------------------------------
# Parent marked done with undone children warns on stderr
# ---------------------------------------------------------------------------


def test_parent_marked_done_with_undone_children_warns_on_stderr(swcw_ready):
    run, workload = swcw_ready
    run("add", "p")
    run("add", "a", "to", "1")
    run("add", "b", "to", "1")
    run("add", "c", "to", "1")

    run("update", "1.1", "status", "done")
    before = workload.read_text()

    result = run("update", "1", "status", "done")
    assert result.returncode == 0, result.stderr
    msg = result.stderr.lower()
    assert "warning" in msg
    assert "done" in msg
    assert workload.read_text() != before
    after = json.loads(run("list", "--json").stdout)["items"]
    assert after[0]["status"] == "done"
