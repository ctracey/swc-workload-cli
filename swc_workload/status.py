"""Status constants, aliases, rollup, and ancestor re-derivation."""

from __future__ import annotations

from typing import Optional

from .cli_error import CLIError
from .tree import find_by_ref

# Status markers used in the persisted JSON tree.
STATUS_NOT_STARTED = "not-started"
STATUS_IN_PROGRESS = "in-progress"
STATUS_DONE = "done"

# Status alias mapping for input shorthand.
STATUS_ALIASES = {
    "not-started": STATUS_NOT_STARTED,
    "not_started": STATUS_NOT_STARTED,
    "notstarted": STATUS_NOT_STARTED,
    "todo": STATUS_NOT_STARTED,
    "in-progress": STATUS_IN_PROGRESS,
    "in_progress": STATUS_IN_PROGRESS,
    "inprogress": STATUS_IN_PROGRESS,
    "wip": STATUS_IN_PROGRESS,
    "done": STATUS_DONE,
    "complete": STATUS_DONE,
}


def derive_parent_status(children: list[dict]) -> str:
    if not children:
        return STATUS_NOT_STARTED
    statuses = [c["status"] for c in children]
    if all(s == STATUS_DONE for s in statuses):
        return STATUS_DONE
    if all(s == STATUS_NOT_STARTED for s in statuses):
        return STATUS_NOT_STARTED
    return STATUS_IN_PROGRESS


def rollup(items: list[dict]) -> None:
    """Re-derive every parent's status from its children, bottom-up.

    Done-sticky only applies on the direct-update path (see cmd_status); the
    rollup path always re-derives. Leaves keep their stored status.
    """
    def walk(node_list):
        for node in node_list:
            children = node.get("children", [])
            if children:
                walk(children)
                node["status"] = derive_parent_status(children)
    walk(items)


def rollup_ancestors(items: list[dict], item_id: str) -> None:
    """Walk path to item_id, then on the way back up, re-derive each ancestor."""
    def walk(node_list) -> bool:
        for node in node_list:
            if node["id"] == item_id:
                return True
            if walk(node.get("children", [])):
                # node is an ancestor — re-derive from its children.
                node["status"] = derive_parent_status(node.get("children", []))
                return True
        return False
    walk(items)


def apply_status_transition(
    items: list[dict],
    ref: str,
    new_status: str,
    *,
    allow_downgrade: bool = False,
) -> tuple[dict, bool, Optional[str]]:
    """Apply a status transition in place. Pure — no I/O.

    `allow_downgrade=True` (used by `reset`) bypasses the done-sticky guard so
    an explicit reset of a done item actually resets. Otherwise, a transition
    that would downgrade `done` is silently preserved (caller is expected to
    skip the file write).

    Parent edits keep the user's value but the caller gets a warning string
    when children disagree; leaf edits flow through full rollup.

    Returns:
        (item, was_preserved, warning).
        - `item` — the matched node (mutated in place unless preserved).
        - `was_preserved` — True if done-sticky kicked in; the item was NOT
          mutated and the caller should skip the file write.
        - `warning` — non-None when a parent was marked done while some
          children are not done; caller should emit to stderr.

    Raises:
        CLIError if `ref` does not resolve.
    """
    found = find_by_ref(items, ref)
    if found is None:
        raise CLIError(f"item {ref} not found")
    item, _, _, _ = found

    if (
        not allow_downgrade
        and item["status"] == STATUS_DONE
        and new_status != STATUS_DONE
    ):
        return item, True, None

    item["status"] = new_status
    warning: Optional[str] = None

    if item.get("children"):
        if new_status == STATUS_DONE:
            not_done = [c for c in item["children"] if c["status"] != STATUS_DONE]
            if not_done:
                warning = (
                    f"warning: parent {ref} marked done while "
                    f"{len(not_done)} of {len(item['children'])} children are not done"
                )
        rollup_ancestors(items, item["id"])
    else:
        rollup(items)

    return item, False, warning
