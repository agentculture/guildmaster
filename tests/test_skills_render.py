"""Tests for ``guild.skills.render`` — agent-major issue body composition (t6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from guild.skills.render import render_issue, render_section

_LEDGER = """\
| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | `tipalti` |
| `communicate` | `steward` | — |
"""


def _seed_root(tmp_path: Path) -> Path:
    for skill, files in {"cicd": ["pr.sh", "lint.sh"], "communicate": []}.items():
        scripts = tmp_path / ".claude" / "skills" / skill / "scripts"
        scripts.mkdir(parents=True)
        for f in files:
            (scripts / f).write_text("#!/bin/sh\n")
        # a subdir that must NOT count as a script
        (scripts / "templates").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(
        "## [0.2.0] - 2026-05-20\n- cicd: add status extension\n\n"
        "## [0.1.0] - 2026-05-01\n- initial\n"
    )
    return tmp_path


# --- render_section (pure) ---

def test_section_new_vs_resync_wording() -> None:
    new = render_section("cicd", scripts=["a.sh"], new=True)
    resync = render_section("cicd", scripts=["a.sh"], new=False)
    assert "New skill" in new
    assert "Resync" in resync


def test_section_origin_block_only_when_origin_given() -> None:
    without = render_section("think", scripts=[], new=True, origin=None)
    with_origin = render_section("think", scripts=[], new=True, origin="agentculture/devague")
    assert "agentculture/devague" not in without
    assert "agentculture/devague" in with_origin
    assert "re-broadcast" in with_origin.lower()


def test_section_lists_scripts_with_count() -> None:
    s = render_section("cicd", scripts=["lint.sh", "pr.sh"], new=True)
    assert "(2 files)" in s
    assert "`lint.sh`" in s and "`pr.sh`" in s


# --- render_issue (integration) ---

def test_issue_is_one_body_with_a_section_per_skill(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    body = render_issue("daria", ["cicd", "communicate"], root=root, ledger_text=_LEDGER)
    # ONE body addressed to the agent, two per-skill sections — never one issue per skill.
    assert body.count("## Skills update for `daria`") == 1
    assert "### `cicd`" in body
    assert "### `communicate`" in body


def test_issue_framing_auto_detected_per_pair(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    # tipalti already consumes cicd (resync) but not communicate (new).
    body = render_issue("tipalti", ["cicd", "communicate"], root=root, ledger_text=_LEDGER)
    cicd_sec = body.split("### `cicd`")[1].split("### `communicate`")[0]
    comm_sec = body.split("### `communicate`")[1]
    assert "Resync" in cicd_sec
    assert "New skill" in comm_sec


def test_issue_origin_block_for_inbound_trio(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    (root / ".claude" / "skills" / "think" / "scripts").mkdir(parents=True)
    body = render_issue(
        "newsib", ["think"], root=root, ledger_text=_LEDGER,
        origins={"think": "agentculture/devague"},
    )
    assert "agentculture/devague" in body


def test_issue_skips_subdir_scripts(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    body = render_issue("daria", ["cicd"], root=root, ledger_text=_LEDGER)
    assert "`templates`" not in body  # the scripts/templates/ subdir is not a script


def test_issue_since_absent_raises(tmp_path: Path) -> None:
    root = _seed_root(tmp_path)
    with pytest.raises(ValueError):
        render_issue("daria", ["cicd"], root=root, ledger_text=_LEDGER, since="9.9.9")
