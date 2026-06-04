"""Helpers for the per-workitem ``meta`` field (1.2.0).

This module is the home of:

- ``parse_bool_flag(value)`` — strict ``true|false`` parser used by
  ``--meta true|false`` and ``--ids true|false`` flags across read commands
  (wired in later work items).
- ``parse_meta_json(value)`` — JSON-object parser used by ``--meta <json>``
  on ``add`` (this work item) and ``start`` / ``complete`` / ``reset``
  (work item 6).

The CLI never interprets the *contents* of a meta object — it only validates
that the supplied value is a JSON object. Dotted-path read/write helpers
land in this module in work item 4.
"""

from __future__ import annotations

import json
from typing import Any

from .cli_error import CLIError


def parse_bool_flag(value: str) -> bool:
    """Strict ``"true"`` / ``"false"`` parser (case-insensitive).

    Rationale: the spec commits to a single spelling for the shared bool
    parser. Lenient variants (``1``/``0``, ``yes``/``no``, whitespace
    padding) would force every caller to remember which were allowed, so
    we reject them up front with a clear ``CLIError``.
    """
    if not isinstance(value, str):
        raise CLIError(
            f"expected 'true' or 'false', got {type(value).__name__}"
        )
    folded = value.casefold()
    if folded == "true":
        return True
    if folded == "false":
        return False
    raise CLIError(
        f"expected 'true' or 'false' (case-insensitive), got {value!r}"
    )


def parse_meta_json(raw: str) -> dict[str, Any]:
    """Parse a ``--meta <json>`` value into a ``dict``.

    Two distinct failure modes, intentionally split so MCP / CLI tests can
    grep for either one:

    - JSON parse failure → ``CLIError("--meta must be valid JSON: ...")``
    - Parsed value is not an object →
      ``CLIError("--meta must be a JSON object, got <type>")``
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CLIError(f"--meta must be valid JSON: {e.msg}") from e
    if not isinstance(parsed, dict):
        raise CLIError(
            f"--meta must be a JSON object, got {_json_type_name(parsed)}"
        )
    return parsed


def _json_type_name(value: Any) -> str:
    """Best-effort JSON type name for error messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
