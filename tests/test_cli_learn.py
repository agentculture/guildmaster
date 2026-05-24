"""Tests for ``guild learn`` — the repo survey."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guild.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_learn_lists_verbs_and_skills(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["learn"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "guild whoami" in out
    assert "guild explain" in out
    # At least one vendored skill shows up (this repo ships the canonical set).
    assert "cicd" in out


def test_learn_json_shape(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["learn", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    verb_names = {v["name"] for v in payload["verbs"]}
    assert {"whoami", "learn", "explain"} <= verb_names
    skill_names = {s["name"] for s in payload["skills"]}
    assert "cicd" in skill_names
    assert payload["version_prompt"] == "CLAUDE.md"
