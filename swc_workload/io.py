"""Persistence — load, save, validate workload.json.

Operates on an explicit folder path; the file name is convention-locked
to `workload.json` inside the supplied folder.
"""

from __future__ import annotations

import json
from pathlib import Path

from .cli_error import CLIError


def workload_path_from_args(args) -> Path:
    """Return the Path to workload.json inside the supplied --workload folder.

    Validates the folder exists and is a directory. The file name is
    convention-locked to `workload.json` — callers pass the folder, not the
    file.
    """
    if not args.workload:
        raise CLIError("--workload <folder> is required")
    folder = Path(args.workload)
    if not folder.exists():
        raise CLIError(f"workload folder does not exist: {folder}")
    if not folder.is_dir():
        raise CLIError(f"--workload expects a folder, got a file: {folder}")
    return folder / "workload.json"


def load_workload(path: Path) -> dict:
    if not path.exists():
        raise CLIError(
            f"no workload at {path}. Run `swc workload init` to create one."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CLIError(
            f"workload.json invalid: {e.msg} at line {e.lineno}, column {e.colno}"
        ) from e
    _validate_shape(data)
    return data


def _validate_shape(data) -> None:
    """Minimal schema check for workload.json.

    Required: top-level must be a dict with `items` (list) and `complete` (bool).
    Each item must have `id` (str), `title` (str), `status` (str), `children`
    (list); recurse into children.

    Raises CLIError with a clear message and JSON-path on first violation.
    """

    def fail(msg: str, path: str) -> None:
        raise CLIError(f"workload.json invalid: {msg} at {path}")

    if not isinstance(data, dict):
        fail("top-level must be an object", "<root>")
    if "items" not in data:
        fail("missing 'items' field", "<root>")
    if not isinstance(data["items"], list):
        fail("'items' must be a list", "<root>.items")
    def walk(items: list, path: str) -> None:
        for i, node in enumerate(items):
            node_path = f"{path}[{i}]"
            if not isinstance(node, dict):
                fail("item must be an object", node_path)
            for field, expected_type, type_name in (
                ("id", str, "string"),
                ("title", str, "string"),
                ("status", str, "string"),
                ("children", list, "list"),
            ):
                if field not in node:
                    fail(f"missing required field '{field}'", node_path)
                if not isinstance(node[field], expected_type):
                    fail(f"'{field}' must be a {type_name}", f"{node_path}.{field}")
            # `meta` is optional. Pre-1.2.0 artefacts don't carry it (REQ-05),
            # but when present it MUST be a JSON object (REQ-10) so callers
            # can rely on the shape downstream.
            if "meta" in node and not isinstance(node["meta"], dict):
                fail("'meta' must be an object", f"{node_path}.meta")
            walk(node["children"], f"{node_path}.children")

    walk(data["items"], "<root>.items")


def save_workload(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def empty_workload() -> dict:
    return {"items": []}


def load_workload_from_args(args) -> tuple[Path, dict]:
    """Resolve workload path + load data for an op that requires a workload."""
    path = workload_path_from_args(args)
    data = load_workload(path)
    data.setdefault("items", [])
    return path, data
