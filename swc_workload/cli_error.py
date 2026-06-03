"""User-facing CLI error type."""

from __future__ import annotations


class CLIError(Exception):
    """Raised for user-facing errors. Message goes to stderr; exit code 1."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code
