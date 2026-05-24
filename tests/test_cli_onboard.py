"""Tests for ``guild onboard`` — the new-sibling ceremony (t8)."""

from __future__ import annotations

import json
from pathlib import Path

from guild.cli import main
from guild.cli._commands import _broadcast
from guild.skills.render import render_issue

_CULTURE = "agents:\n- suffix: guildmaster\n  backend: claude\n"
_LEDGER = """\
# Skill sources

| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `tipalti` |
| `think` | `devague` | — |
"""


def _seed(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "culture.yaml").write_text(_CULTURE)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - 2026-05-01\n- init\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skill-sources.md").write_text(_LEDGER)
    for skill in ("cicd", "think"):
        d = tmp_path / ".claude" / "skills" / skill
        (d / "scripts").mkdir(parents=True)
        (d / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: the {skill} skill\ntype: command\n---\n"
        )
    return tmp_path


def test_onboard_dry_run_one_issue_plus_diff_plus_verification(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    def _boom(*a, **k):
        raise AssertionError("post_issue called during dry-run")

    monkeypatch.setattr(_broadcast, "post_issue", _boom)
    rc = main(["onboard", "--agent", "newsib", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    # ONE consolidated issue, all canonical sections + identity section.
    body = payload["issue"]["body"]
    assert "### `cicd`" in body and "### `think`" in body
    assert "culture.yaml" in body and "CLAUDE.md" in body  # identity-setup section
    # ledger diff + verification record present in dry-run, nothing written.
    assert "newsib" in payload["ledger_diff"]
    assert payload["verification"]["agent"] == "agentculture/newsib"
    assert sorted(payload["verification"]["skills"]) == ["cicd", "think"]
    assert not (Path.cwd() / "docs" / "onboarding").exists()


def test_onboard_inbound_origin_attribution(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_broadcast, "post_issue", lambda *a, **k: None)
    rc = main(["onboard", "--agent", "newsib", "--json"])
    assert rc == 0
    body = json.loads(capsys.readouterr().out)["issue"]["body"]
    # think is inbound -> origin block names devague.
    assert "agentculture/devague" in body


def test_onboard_uses_same_engine_as_teach(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.chdir(root)
    rc = main(["onboard", "--agent", "newsib", "--json"])
    assert rc == 0
    body = json.loads(capsys.readouterr().out)["issue"]["body"]
    # The kit body is exactly render_issue's output (no separate broadcast path).
    expected_kit = render_issue(
        "agentculture/newsib",
        ["cicd", "think"],
        root=root,
        ledger_text=_LEDGER,
        origins={"think": "agentculture/devague"},
    )
    # Every per-skill section render_issue produced is embedded verbatim.
    for marker in ("### `cicd`", "### `think`", "New skill — add it fresh."):
        assert marker in expected_kit and marker in body


def test_onboard_apply_posts_writes_ledger_and_pins(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    monkeypatch.chdir(root)
    calls = []
    monkeypatch.setattr(_broadcast, "post_issue", lambda r, repo, title, b: calls.append(repo))
    rc = main(["onboard", "--agent", "newsib", "--apply", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert calls == ["agentculture/newsib"]
    assert out["ledger_written"] is True
    # ledger now lists newsib as a downstream consumer of every canonical row.
    ledger = (root / "docs" / "skill-sources.md").read_text()
    assert "`newsib`" in ledger
    # verification record written.
    ver = json.loads((root / "docs" / "onboarding" / "newsib.json").read_text())
    assert ver["agent"] == "agentculture/newsib"


def test_onboard_backend_acp_uses_agents_md(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_broadcast, "post_issue", lambda *a, **k: None)
    rc = main(["onboard", "--agent", "newsib", "--backend", "acp", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["backend"] == "acp"
    # acp sibling must be told to create AGENTS.md, not CLAUDE.md.
    assert "AGENTS.md" in out["issue"]["body"]


def test_onboard_apply_ledger_idempotent(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(_broadcast, "post_issue", lambda *a, **k: None)
    main(["onboard", "--agent", "newsib", "--apply"])
    first = (root / "docs" / "skill-sources.md").read_text()
    main(["onboard", "--agent", "newsib", "--apply"])
    second = (root / "docs" / "skill-sources.md").read_text()
    assert first == second  # second apply changes zero bytes
