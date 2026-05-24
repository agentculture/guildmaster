"""Unified CLI entry point for guild.

Every handler raises :class:`guild.cli._errors.GuildError` on failure;
``main()`` catches it via :func:`_dispatch` and routes through
:mod:`guild.cli._output`. Argparse errors route through
``_GuildArgumentParser`` so they share the same structured output.
"""

from __future__ import annotations

import argparse
import sys

from guild import __version__
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_error


class _GuildArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`."""

    def error(self, message: str) -> None:  # type: ignore[override]
        err = GuildError(
            code=EXIT_USER_ERROR,
            message=message,
            remediation=f"run '{self.prog} --help' to see valid arguments",
        )
        emit_error(err)
        raise SystemExit(err.code)


def _build_parser() -> argparse.ArgumentParser:
    # Deferred import to avoid coupling the parser module to the command modules
    # at import time (matches the afi-cli pattern; cheap insurance).
    from guild.cli._commands import explain as _explain_cmd
    from guild.cli._commands import learn as _learn_cmd
    from guild.cli._commands import teach as _teach_cmd
    from guild.cli._commands import whoami as _whoami_cmd

    parser = _GuildArgumentParser(
        prog="guild",
        description="guild — an agent and CLI that manages skills for the AgentCulture mesh",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_GuildArgumentParser)

    _whoami_cmd.register(sub)
    _learn_cmd.register(sub)
    _explain_cmd.register(sub)
    _teach_cmd.register(sub)

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    try:
        rc = args.func(args)
    except GuildError as err:
        emit_error(err)
        return err.code
    except Exception as err:  # noqa: BLE001 - last-resort: wrap so no traceback leaks
        wrapped = GuildError(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {err.__class__.__name__}: {err}",
            remediation="file a bug at https://github.com/agentculture/guildmaster/issues",
        )
        emit_error(wrapped)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
