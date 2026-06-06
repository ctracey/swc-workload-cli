"""Registered CLI subcommand classes.

Each entry in `ALL` is an instance of `Command` (or a subclass). The list is
explicit — `cli.build_parser()` iterates it to register subparsers and wire up
the `args.func` dispatch.
"""

from __future__ import annotations

from .add_command import AddCommand
from .command import Command
from .complete_command import CompleteCommand
from .delete_command import DeleteCommand
from .exists_command import ExistsCommand
from .find_by_meta_command import FindByMetaCommand
from .find_command import FindCommand
from .get_command import GetCommand
from .init_command import InitCommand
from .list_command import ListCommand
from .move_command import MoveCommand
from .rename_command import RenameCommand
from .reset_command import ResetCommand
from .start_command import StartCommand
from .summary_command import SummaryCommand
from .update_meta_command import UpdateMetaCommand

ALL: list[Command] = [
    InitCommand(),
    ExistsCommand(),
    ListCommand(),
    FindCommand(),
    SummaryCommand(),
    GetCommand(),
    FindByMetaCommand(),
    AddCommand(),
    RenameCommand(),
    DeleteCommand(),
    MoveCommand(),
    ResetCommand(),
    StartCommand(),
    CompleteCommand(),
    UpdateMetaCommand(),
]
