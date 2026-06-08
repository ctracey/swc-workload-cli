"""Helpers for the per-workitem ``meta`` field (1.2.0).

This module is the home of:

- ``parse_bool_flag(value)`` — strict ``true|false`` parser used by
  ``--meta true|false`` and ``--ids true|false`` flags across read commands.
- ``parse_meta_json(value)`` — JSON-object parser used by ``--meta <json>``
  on ``add`` and (work item 6) ``start`` / ``complete`` / ``reset``. Error
  messages name the ``--meta`` flag verbatim.
- ``parse_meta_object(value, label)`` — flag-agnostic core. Same parse-and-
  validate semantics as ``parse_meta_json`` but the caller chooses the
  label that appears in error messages (e.g. ``"<json-value>"`` for the
  ``update-meta`` empty-path branch, where the user never typed a flag).
- ``parse_meta_value(value)`` — JSON parser that accepts ANY JSON type
  (object, array, string, number, boolean, null). Used by ``update-meta``
  at non-empty paths where the leaf may be any JSON value.
- ``parse_path(raw)`` — split a dotted path into a tuple of segments.
- ``read_at_path(meta, path)`` / ``write_at_path(meta, path, value)`` —
  dotted-path traversal helpers used by ``get``, ``update-meta``, and
  ``find-by-meta``.

The CLI never interprets the *contents* of a meta object — it only
validates that the supplied value is a JSON object (for ``--meta <json>``
and the empty-path root) and that dotted-path traversal does not silently
clobber co-resident data.
"""

from __future__ import annotations

import json
import re as _re
from typing import Any

_BRACKET_IDX_RE = _re.compile(r"\[(\d+)\]")

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


def parse_meta_object(raw: str, *, label: str) -> dict[str, Any]:
    """Parse ``raw`` as a JSON object, naming ``label`` in error messages.

    The flag-agnostic core behind ``parse_meta_json``. Callers pick the
    label so users see the argument they actually typed — ``"--meta"`` for
    the ``add --meta <json>`` flag, ``"<json-value>"`` for the
    ``update-meta`` empty-path positional, etc.

    Two distinct failure modes:

    - JSON parse failure → ``CLIError("<label> must be valid JSON: ...")``
    - Parsed value is not an object →
      ``CLIError("<label> must be a JSON object, got <type>")``
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise CLIError(f"{label} must be valid JSON: {e.msg}") from e
    if not isinstance(parsed, dict):
        raise CLIError(
            f"{label} must be a JSON object, got {_json_type_name(parsed)}"
        )
    return parsed


def parse_meta_json(raw: str) -> dict[str, Any]:
    """Parse a ``--meta <json>`` value into a ``dict``.

    Thin wrapper around :func:`parse_meta_object` that pins the label to
    ``"--meta"`` so callers using the ``--meta`` flag (``add``, and in
    work item 6 ``start``/``complete``/``reset``) get error messages that
    name the flag verbatim. MCP integration tests grep for that string.
    """
    return parse_meta_object(raw, label="--meta")


def parse_meta_value(raw: str) -> Any:
    """Parse a ``<json-value>`` argument into a Python value.

    Accepts any JSON type — object, array, string, number, boolean, null.
    Used by ``update-meta <ref> <path> <json-value>`` for non-empty paths,
    where the leaf can be any JSON value. The empty-path branch keeps
    using ``parse_meta_json`` (object required).

    Failure mode:
    - JSON parse failure → ``CLIError("<value> is not valid JSON: ...")``.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise CLIError(f"<value> is not valid JSON: {e.msg}") from e


def parse_path(raw: str) -> tuple[str, ...]:
    """Split a dotted path into a tuple of segments.

    - ``""`` returns ``()`` (root).
    - Segments are split on ``.``; ``:`` and other punctuation are valid
      segment characters per the spec.
    - ``[N]`` bracket notation is expanded into a separate index segment so
      that ``tags[0]`` and ``tags[0].name`` work naturally.
      ``tags[0]`` → ``("tags", "0")``;
      ``steps[0].name`` → ``("steps", "0", "name")``.

    No further validation is performed — adjacent dots / empty segments are
    preserved as-is. Path-segment validity is the job of ``read_at_path`` /
    ``write_at_path``.
    """
    if raw == "":
        return ()
    segments: list[str] = []
    for part in raw.split("."):
        if "[" not in part:
            segments.append(part)
        else:
            for seg in _BRACKET_IDX_RE.split(part):
                if seg:  # skip empty artifacts from split
                    segments.append(seg)
    return tuple(segments)


def read_at_path(meta: dict, path: tuple[str, ...]) -> tuple[bool, Any]:
    """Walk ``meta`` to the dotted ``path``; return ``(found, value)``.

    - Empty path returns ``(True, meta)`` — the root dict itself, **by
      reference**. Callers that mutate the returned value will mutate the
      live item dict; copy first if that is not the intent.
    - Missing intermediate / missing leaf / non-object intermediate →
      ``(False, None)``.
    - Present value (including falsy values: ``None``, ``0``, ``False``,
      ``""``) → ``(True, value)``.
    - Array intermediates are traversed by integer index (``"0"``, ``"1"``
      …). A non-integer segment on a list, or an out-of-bounds index, is
      a miss.

    Note: a non-object, non-array intermediate is treated as a *miss* for
    reads. Writes are asymmetric — see ``write_at_path``.
    """
    cursor: Any = meta
    for segment in path:
        if isinstance(cursor, list):
            try:
                idx = int(segment)
            except ValueError:
                return (False, None)
            if idx < 0 or idx >= len(cursor):
                return (False, None)
            cursor = cursor[idx]
        elif isinstance(cursor, dict):
            if segment not in cursor:
                return (False, None)
            cursor = cursor[segment]
        else:
            return (False, None)
    return (True, cursor)


def write_at_path(meta: dict, path: tuple[str, ...], value: Any) -> None:
    """Set ``value`` at the dotted ``path`` inside ``meta`` (in-place).

    - Missing intermediate objects are created as ``{}``.
    - Existing leaf at the final segment is replaced wholly (no merge).
    - Empty path is invalid here — the caller (``update-meta`` with
      empty path) handles whole-meta replacement directly.
    - Raises ``CLIError`` when an intermediate segment exists and is
      not a dict (would silently clobber co-resident data).

    The asymmetry with ``read_at_path`` is intentional: writes are
    explicit user intent, so unexpected non-object intermediates are
    surfaced rather than silently overwritten.
    """
    if not path:
        raise CLIError(
            "write_at_path requires a non-empty path; "
            "callers must handle empty-path replacement directly."
        )
    cursor: dict = meta
    for i, segment in enumerate(path[:-1]):
        if segment not in cursor:
            new_child: dict = {}
            cursor[segment] = new_child
            cursor = new_child
            continue
        existing = cursor[segment]
        if not isinstance(existing, dict):
            traversed = ".".join(path[: i + 1])
            raise CLIError(
                f"cannot traverse non-object value at meta path "
                f"'{traversed}' (existing value is {_json_type_name(existing)})"
            )
        cursor = existing
    cursor[path[-1]] = value


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
