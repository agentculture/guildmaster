"""Tests for ``guild whoami`` — the offline identity probe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guild import __version__
from guild.cli import main

_CULTURE_YAML = "agents:\n- suffix: guildmaster\n  backend: claude\n"


def _seed_repo(tmp_path: Path, culture_yaml: str | None = _CULTURE_YAML) -> Path:
    (tmp_path / ".git").mkdir()
    if culture_yaml is not None:
        (tmp_path / "culture.yaml").write_text(culture_yaml)
    return tmp_path


def test_whoami_reports_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(_seed_repo(tmp_path))
    rc = main(["whoami"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"guild {__version__}" in out
    assert "guildmaster" in out
    assert "claude" in out


def test_whoami_json_is_parseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(_seed_repo(tmp_path))
    rc = main(["whoami", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["version"] == __version__
    assert payload["agents"][0]["suffix"] == "guildmaster"
    assert payload["agents"][0]["backend"] == "claude"


def test_whoami_without_culture_yaml_is_graceful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(_seed_repo(tmp_path, culture_yaml=None))
    rc = main(["whoami"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"guild {__version__}" in out
    assert "none declared" in out
