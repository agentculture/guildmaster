"""Tests for ``guild show`` — the per-agent config view (#12).

These exercise the *real* vendored ``agent-config`` skill end-to-end: the
repo's ``.claude/skills/agent-config/`` is copied into a temp git repo and the
actual ``show.sh`` runs under bash. So they double as a guard that the vendored
script stays runnable.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from guild.cli import main
from guild.cli._errors import EXIT_USER_ERROR

# The repo's vendored skill, copied into each temp repo so show.sh resolves.
_VENDORED_SKILL = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "agent-config"

_CULTURE = "agents:\n- suffix: daria\n  backend: acp\n  model: nova\n"


def _seed_repo(tmp_path: Path) -> Path:
    """A git repo that vendors the agent-config skill (so `guild show` resolves)."""
    (tmp_path / ".git").mkdir()
    dst = tmp_path / ".claude" / "skills" / "agent-config"
    dst.parent.mkdir(parents=True)
    shutil.copytree(_VENDORED_SKILL, dst)
    return tmp_path


def _seed_target(parent: Path, name: str, *, prompt: str | None, culture: bool, skills: bool):
    """Create an agent directory to inspect."""
    d = parent / name
    d.mkdir()
    if prompt is not None:
        (d / prompt).write_text(f"# {name} prompt\n")
    if culture:
        (d / "culture.yaml").write_text(_CULTURE)
    if skills:
        s = d / ".claude" / "skills" / "demo"
        (s / "scripts").mkdir(parents=True)
        (s / "SKILL.md").write_text("---\nname: demo\ndescription: a demo skill\n---\n")
    return d


def test_show_path_mode_full_config(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "agentx", prompt="AGENTS.md", culture=True, skills=True)
    monkeypatch.chdir(repo)
    rc = main(["show", "agentx"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "AGENTS.md" in out  # detected prompt file
    assert "backend: acp" in out  # culture.yaml printed verbatim
    assert "demo" in out  # skills index line


def test_show_missing_culture_yaml(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "noconf", prompt="CLAUDE.md", culture=False, skills=False)
    monkeypatch.chdir(repo)
    rc = main(["show", "noconf"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(missing)" in out  # culture.yaml absent


def test_show_no_skills(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "bare", prompt="CLAUDE.md", culture=True, skills=False)
    monkeypatch.chdir(repo)
    rc = main(["show", "bare"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(no skills)" in out


def test_show_suffix_mode_resolves_via_manifest(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    # Dir name differs from the suffix so cwd has no `./daria` — forces suffix mode.
    target = _seed_target(repo, "regagent", prompt="AGENTS.md", culture=True, skills=False)
    # A Culture server manifest mapping the suffix → its directory.
    manifest = repo / "server.yaml"
    manifest.write_text(f"agents:\n  daria:\n    directory: {target}\n")
    # Point culture_server_yaml at the manifest via skills.local.yaml.
    (repo / ".claude" / "skills.local.yaml").write_text(f"culture_server_yaml: {manifest}\n")
    monkeypatch.chdir(repo)
    rc = main(["show", "daria"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "backend: acp" in out  # resolved + printed the target's culture.yaml


def test_show_unknown_suffix_is_user_error(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    manifest = repo / "server.yaml"
    manifest.write_text("agents:\n  daria:\n    directory: /tmp/daria\n")
    (repo / ".claude" / "skills.local.yaml").write_text(f"culture_server_yaml: {manifest}\n")
    monkeypatch.chdir(repo)
    rc = main(["show", "ghost"])  # not in the manifest → show.sh exits 2
    assert rc == EXIT_USER_ERROR
    assert "no agent registered" in capsys.readouterr().err


def test_show_script_not_found_outside_repo(tmp_path, monkeypatch, capsys):
    # A git repo that does NOT vendor the skill → clear env error.
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    rc = main(["show", "whatever"])
    assert rc != 0
    assert "skill script not found" in capsys.readouterr().err


@pytest.mark.parametrize("prompt_file", ["CLAUDE.md", "AGENTS.md", "GEMINI.md"])
def test_show_detects_each_backend_prompt_file(tmp_path, monkeypatch, capsys, prompt_file):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "agent", prompt=prompt_file, culture=True, skills=False)
    monkeypatch.chdir(repo)
    rc = main(["show", "agent"])
    assert rc == 0
    assert prompt_file in capsys.readouterr().out


def test_show_json_path_mode_structured(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "agentx", prompt="AGENTS.md", culture=True, skills=True)
    monkeypatch.chdir(repo)
    rc = main(["show", "agentx", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == "agentx"
    assert payload["prompt_file"] == "AGENTS.md"
    assert "agentx prompt" in payload["prompt"]
    assert payload["culture_yaml"]["agents"][0]["backend"] == "acp"
    assert [s["name"] for s in payload["skills"]] == ["demo"]


def test_show_json_suffix_mode(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    # Dir name differs from the suffix so cwd has no `./daria` — forces suffix mode.
    target = _seed_target(repo, "regagent", prompt="AGENTS.md", culture=True, skills=False)
    manifest = repo / "server.yaml"
    manifest.write_text(f"agents:\n  daria:\n    directory: {target}\n")
    (repo / ".claude" / "skills.local.yaml").write_text(f"culture_server_yaml: {manifest}\n")
    monkeypatch.chdir(repo)
    rc = main(["show", "daria", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dir"] == str(target)
    assert payload["culture_yaml"]["agents"][0]["suffix"] == "daria"


def test_show_json_missing_culture_yaml_is_null(tmp_path, monkeypatch, capsys):
    repo = _seed_repo(tmp_path)
    _seed_target(repo, "noconf", prompt="CLAUDE.md", culture=False, skills=False)
    monkeypatch.chdir(repo)
    rc = main(["show", "noconf", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["culture_yaml"] is None
    assert payload["skills"] == []
