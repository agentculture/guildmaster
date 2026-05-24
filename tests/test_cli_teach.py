"""Tests for ``guild teach`` — agent-major skill propagation (t7)."""

from __future__ import annotations

import json
from pathlib import Path

from guild.cli import main
from guild.cli._commands import _broadcast

_CULTURE = "agents:\n- suffix: guildmaster\n  backend: claude\n"
_LEDGER = """\
# Skill sources

| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `tipalti` |
| `communicate` | `steward` | — |
"""
_CHANGELOG = (
    "# Changelog\n\n## [0.2.0] - 2026-05-20\n- cicd: status extension\n\n"
    "## [0.1.0] - 2026-05-01\n- communicate: initial\n"
)


def _seed(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "culture.yaml").write_text(_CULTURE)
    (tmp_path / "CHANGELOG.md").write_text(_CHANGELOG)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skill-sources.md").write_text(_LEDGER)
    for skill in ("cicd", "communicate"):
        d = tmp_path / ".claude" / "skills" / skill
        (d / "scripts").mkdir(parents=True)
        (d / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: the {skill} skill\ntype: command\n---\n"
        )
    return tmp_path


def test_teach_two_skills_one_agent_one_bundled_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    rc = main(["teach", "--skill", "cicd", "--skill", "communicate", "--to", "tipalti", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert len(payload["issues"]) == 1  # ONE issue for the one agent, not one per skill
    issue = payload["issues"][0]
    assert issue["repo"] == "agentculture/tipalti"  # bare name got the org prefix
    assert "### `cicd`" in issue["body"] and "### `communicate`" in issue["body"]


def test_teach_no_skill_selected_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    rc = main(["teach", "--to", "tipalti"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "no implicit default" in err or "no skills selected" in err


def test_teach_all_selects_canonical_set(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    rc = main(["teach", "--all", "--to", "daria", "--json"])
    assert rc == 0
    issue = json.loads(capsys.readouterr().out)["issues"][0]
    assert "### `cicd`" in issue["body"] and "### `communicate`" in issue["body"]


def test_teach_ledger_fallback_when_no_to(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    # cicd's only ledger consumer is tipalti -> it becomes the target, framed as resync.
    rc = main(["teach", "--skill", "cicd", "--json"])
    assert rc == 0
    issue = json.loads(capsys.readouterr().out)["issues"][0]
    assert issue["repo"] == "agentculture/tipalti"
    assert "Resync" in issue["body"]


def test_teach_dry_run_posts_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(_seed(tmp_path))

    def _boom(*a, **k):  # must never be called in dry-run
        raise AssertionError("post_issue called during dry-run")

    monkeypatch.setattr(_broadcast, "post_issue", _boom)
    rc = main(["teach", "--skill", "cicd", "--to", "tipalti"])
    assert rc == 0


def test_teach_apply_posts_one_issue_per_agent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    calls = []
    monkeypatch.setattr(
        _broadcast, "post_issue", lambda root, repo, title, body: calls.append(repo)
    )
    rc = main(["teach", "--skill", "cicd", "--to", "tipalti", "--to", "daria", "--apply"])
    assert rc == 0
    assert calls == ["agentculture/tipalti", "agentculture/daria"]


def test_teach_apply_nonzero_on_post_failure(tmp_path, monkeypatch):
    from guild.cli._errors import EXIT_USER_ERROR, GuildError

    monkeypatch.chdir(_seed(tmp_path))

    def _fail(*a, **k):
        raise GuildError(code=EXIT_USER_ERROR, message="boom", remediation="x")

    monkeypatch.setattr(_broadcast, "post_issue", _fail)
    rc = main(["teach", "--skill", "cicd", "--to", "tipalti", "--apply"])
    assert rc == EXIT_USER_ERROR
