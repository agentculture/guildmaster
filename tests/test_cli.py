"""End-to-end tests for the guild CLI surface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from guild import __version__
from guild.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_flag_prints_version_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`guild --version` prints `guild <version>` to stdout and exits 0."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"guild {__version__}"


def test_no_args_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`guild` with no args prints help to stdout and returns 0 (doesn't error)."""
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage: guild" in out
    for verb in ("whoami", "learn", "explain"):
        assert verb in out


def test_unknown_command_exits_with_user_error_code(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown subcommand routes through GuildError → exit 1 + 'error:' on stderr."""
    with pytest.raises(SystemExit) as excinfo:
        main(["bogus"])
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "hint:" in err


def test_python_m_guild_version() -> None:
    """`python -m guild --version` works (proves __main__.py).

    Uses ``sys.executable`` so the subprocess runs in the same interpreter /
    venv as the test runner.
    """
    result = subprocess.run(
        [sys.executable, "-m", "guild", "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"guild {__version__}"


def test_guild_entry_point_declared() -> None:
    import tomllib

    data = tomllib.load(open(REPO_ROOT / "pyproject.toml", "rb"))
    assert data["project"]["scripts"].get("guild") == "guild.cli:main"


def test_dispatch_wraps_unexpected_exception(capsys: pytest.CaptureFixture[str]) -> None:
    """A non-GuildError raised by a handler is wrapped, not re-raised."""
    import argparse

    from guild.cli import _dispatch

    args = argparse.Namespace(func=lambda _a: (_ for _ in ()).throw(ValueError("boom")))
    rc = _dispatch(args)
    assert rc != 0
    assert "unexpected: ValueError: boom" in capsys.readouterr().err
