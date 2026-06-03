"""Input validation — title format rules."""

from __future__ import annotations

import re

from .cli_error import CLIError

# Reject titles that look like the CLI's own numbering (e.g. "2.3 foo"). A
# single integer prefix like "12 monkeys" is allowed — only dotted numbers are
# treated as the CLI's reserved numbering format (REQ-04).
NUMBER_PREFIX_RE = re.compile(r"^\d+(?:\.\d+)+\s+")


def validate_title(title: str) -> None:
    if not title or not title.strip():
        raise CLIError("title is required and must be non-empty")
    if NUMBER_PREFIX_RE.match(title):
        raise CLIError(
            f"title cannot start with a dotted-number prefix; numbers are assigned automatically. Got: {title!r}"
        )
