"""Tests for ``guild overview`` — the read-only skills-supplier surface (#12)."""

from __future__ import annotations

import json
from pathlib import Path

from guild import __version__
from guild.cli import main

_CULTURE = "agents:\n- suffix: guildmaster\n  backend: claude\n"

# Pre-cutover: a consumer-side ledger (Upstream / Notes), no Downstream column.
_CONSUMER_LEDGER = """\
# Skill sources

| Skill | Upstream | Notes |
|-------|----------|-------|
| `cicd` | `steward` | PR lifecycle |
| `communicate` | `steward` | issue I/O |
"""

# Post-cutover: a supplier ledger with a Downstream column + consumers.
_SUPPLIER_LEDGER = """\
# Skill sources

| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `guildmaster` | `tipalti`, `daria` |
| `communicate` | `guildmaster` | `tipalti` |
"""


def _seed(tmp_path: Path, ledger: str) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "culture.yaml").write_text(_CULTURE)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skill-sources.md").write_text(ledger)
    # Two canonical skills + guildmaster's own skills (teach/onboard verbs and
    # the `guild` affordance skill — all excluded from the canonical set).
    for skill in ("cicd", "communicate", "teach", "onboard", "guild"):
        d = tmp_path / ".claude" / "skills" / skill
        (d / "scripts").mkdir(parents=True)
        (d / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: the {skill} skill\ntype: command\n---\n"
        )
    return tmp_path


def test_overview_all_lists_canonical_set_excluding_self_skills(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scope: all" in out
    # Canonical skills present; guildmaster's own skills are NOT canonical.
    assert "`cicd`" in out and "`communicate`" in out
    assert "`teach`" not in out and "`onboard`" not in out
    assert "`guild`" not in out


def test_overview_all_json_structure_and_consumers(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] == "all"
    assert payload["version"] == __version__
    assert payload["has_supplier_ledger"] is True
    names = {s["name"] for s in payload["canonical_skills"]}
    assert names == {"cicd", "communicate"}
    cicd = next(s for s in payload["canonical_skills"] if s["name"] == "cicd")
    assert cicd["consumers"] == ["tipalti", "daria"]
    assert payload["agents"] == ["tipalti", "daria"]


def test_overview_all_drift_signals(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--json"])
    assert rc == 0
    drift = json.loads(capsys.readouterr().out)["drift"]
    # No uncovered or unledgered skills here (both tracked + both have consumers).
    assert drift["uncovered_skills"] == []
    assert drift["unledgered_skills"] == []
    # daria consumes cicd but not communicate → a kit gap.
    assert drift["agent_gaps"]["daria"] == ["communicate"]
    # tipalti consumes both → no gap.
    assert drift["agent_gaps"]["tipalti"] == []


def test_overview_pre_cutover_consumer_ledger_degrades_gracefully(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _CONSUMER_LEDGER))
    rc = main(["overview", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    # No Downstream column → no supplier ledger; canonical set still reported.
    assert payload["has_supplier_ledger"] is False
    assert payload["agents"] == []
    assert {s["name"] for s in payload["canonical_skills"]} == {"cicd", "communicate"}
    # Human render explains the pre-cutover state.
    assert main(["overview"]) == 0
    out = capsys.readouterr().out
    assert "No supplier ledger yet" in out and "cutover" in out


def test_overview_self_reports_kit_and_gaps(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--scope", "self", "daria", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] == "self"
    assert payload["agent"] == "daria"
    assert payload["registered"] is True
    assert payload["kit"] == ["cicd"]
    assert payload["gaps"] == ["communicate"]


def test_overview_self_unregistered_agent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--scope", "self", "ghost", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["registered"] is False
    assert payload["kit"] == []
    assert payload["gaps"] == ["cicd", "communicate"]


def test_overview_self_owner_repo_form_matches_on_bare_name(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--scope", "self", "agentculture/daria", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["registered"] is True
    assert payload["kit"] == ["cicd"]


def test_overview_self_without_agent_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "--scope", "self"])
    assert rc != 0
    assert "requires an agent" in capsys.readouterr().err


def test_overview_all_with_agent_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path, _SUPPLIER_LEDGER))
    rc = main(["overview", "daria"])
    assert rc != 0
    assert "only valid with --scope self" in capsys.readouterr().err


# --- `guild overview --scope mesh` — live filesystem survey ---------------


def _make_skill(repo: Path, name: str, *, script: str = "#!/bin/sh\n") -> None:
    """Create ``<repo>/.claude/skills/<name>/`` with a SKILL.md + a script whose
    body (``script``) drives the content fingerprint."""
    d = repo / ".claude" / "skills" / name
    (d / "scripts").mkdir(parents=True)
    (d / "scripts" / "run.sh").write_text(script)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: the {name} skill\ntype: command\n---\n"
    )


def _seed_workspace(tmp_path: Path) -> Path:
    """A workspace with three agent repos; returns the guildmaster repo (chdir
    target / canonical reference). Canonical set = `cicd`, `communicate`."""
    ws = tmp_path / "ws"
    guild = ws / "guild"
    (guild / ".git").mkdir(parents=True)
    (guild / "culture.yaml").write_text(_CULTURE)
    _make_skill(guild, "cicd", script="#!/bin/sh\n# canonical cicd\n")
    _make_skill(guild, "communicate", script="#!/bin/sh\n# canonical communicate\n")
    _make_skill(guild, "teach")  # SELF_SKILL — excluded from the canonical set

    # agentA: cicd identical (current), communicate differs (stale), none missing.
    a = ws / "agentA"
    a.mkdir()
    (a / "culture.yaml").write_text("suffix: aaa\nbackend: acp\n")  # flat single-agent form
    _make_skill(a, "cicd", script="#!/bin/sh\n# canonical cicd\n")
    _make_skill(a, "communicate", script="#!/bin/sh\n# OLD communicate\n")

    # agentB: only a non-canonical extra skill → both canonical skills missing.
    b = ws / "agentB"
    b.mkdir()
    (b / "culture.yaml").write_text("agents:\n- suffix: bbb\n  backend: claude\n")
    _make_skill(b, "some-extra")
    return guild


def test_overview_mesh_reports_current_stale_missing(tmp_path, monkeypatch, capsys):
    guild = _seed_workspace(tmp_path)
    monkeypatch.chdir(guild)
    rc = main(["overview", "--scope", "mesh", "--workspace-root", str(guild.parent), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] == "mesh"
    assert [c["name"] for c in payload["canonical_skills"]] == ["cicd", "communicate"]
    agents = {a["suffix"]: a for a in payload["agents"]}
    # guildmaster is the reference — everything current.
    assert agents["guildmaster"]["missing"] == [] and agents["guildmaster"]["stale"] == []
    # agentA: communicate differs (stale), cicd identical (current), nothing missing.
    assert agents["aaa"]["stale"] == ["communicate"]
    assert agents["aaa"]["missing"] == []
    # agentB: lacks both canonical skills; its non-canonical skill is "extra".
    assert set(agents["bbb"]["missing"]) == {"cicd", "communicate"}
    assert agents["bbb"]["extra"] == ["some-extra"]


def test_overview_mesh_markdown(tmp_path, monkeypatch, capsys):
    guild = _seed_workspace(tmp_path)
    monkeypatch.chdir(guild)
    rc = main(["overview", "--scope", "mesh", "--workspace-root", str(guild.parent)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "scope: mesh" in out
    assert "3 agent(s)" in out
    assert "Missing & stale detail" in out
    assert "stale `communicate`" in out


def test_overview_mesh_no_agents(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "solo"
    (repo / ".git").mkdir(parents=True)
    (repo / "culture.yaml").write_text(_CULTURE)
    empty_ws = tmp_path / "empty"
    empty_ws.mkdir()
    monkeypatch.chdir(repo)
    rc = main(["overview", "--scope", "mesh", "--workspace-root", str(empty_ws)])
    assert rc == 0
    assert "No agents found" in capsys.readouterr().out


def test_overview_mesh_rejects_agent_positional(tmp_path, monkeypatch, capsys):
    guild = _seed_workspace(tmp_path)
    monkeypatch.chdir(guild)
    rc = main(["overview", "--scope", "mesh", "somebody"])
    assert rc != 0
    assert "only valid with --scope self" in capsys.readouterr().err
