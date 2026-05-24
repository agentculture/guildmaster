"""Tests for ``guild explain <topic>``."""

from __future__ import annotations

from pathlib import Path

import pytest

from guild.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_explain_skill_prints_skill_md(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["explain", "cicd"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "name: cicd" in out  # the vendored SKILL.md frontmatter


def test_explain_verb_prints_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["explain", "whoami"])
    assert rc == 0
    assert "guild whoami" in capsys.readouterr().out


def test_explain_unknown_topic_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["explain", "nope-not-a-topic"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unknown topic" in err
    assert "valid topics" in err


@pytest.mark.parametrize("verb", ["teach", "onboard"])
def test_explain_knows_the_supplier_verbs(
    verb: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # The supplier verbs must be in the inventory — explain must not 404 them.
    monkeypatch.chdir(REPO_ROOT)
    rc = main(["explain", verb])
    assert rc == 0
    assert f"guild {verb}" in capsys.readouterr().out
