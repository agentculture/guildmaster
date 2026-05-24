"""Tests for ``_broadcast.post_issue`` — cwd + exit-code mapping (PR #11 review)."""

from __future__ import annotations

from pathlib import Path

import pytest

from guild.cli._commands import _broadcast
from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError


def _fake_repo(tmp_path: Path, exit_code: int) -> Path:
    script = tmp_path / ".claude" / "skills" / "communicate" / "scripts" / "post-issue.sh"
    script.parent.mkdir(parents=True)
    # Record the cwd it was launched from, then exit with the chosen code.
    script.write_text(f"#!/usr/bin/env bash\npwd > cwd_marker.txt\nexit {exit_code}\n")
    script.chmod(0o755)
    return tmp_path


def test_post_issue_runs_from_repo_root(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path, 0)
    _broadcast.post_issue(root, "agentculture/x", "title", "body")
    recorded = (root / "cwd_marker.txt").read_text().strip()
    assert Path(recorded).resolve() == root.resolve()


def test_post_issue_exit_2_is_env_error(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path, 2)  # e.g. agtag missing
    with pytest.raises(GuildError) as exc:
        _broadcast.post_issue(root, "agentculture/x", "title", "body")
    assert exc.value.code == EXIT_ENV_ERROR


def test_post_issue_other_nonzero_is_user_error(tmp_path: Path) -> None:
    root = _fake_repo(tmp_path, 1)
    with pytest.raises(GuildError) as exc:
        _broadcast.post_issue(root, "agentculture/x", "title", "body")
    assert exc.value.code == EXIT_USER_ERROR


def test_post_issue_missing_script_is_env_error(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()  # repo without the communicate skill vendored
    with pytest.raises(GuildError) as exc:
        _broadcast.post_issue(tmp_path, "agentculture/x", "title", "body")
    assert exc.value.code == EXIT_ENV_ERROR
