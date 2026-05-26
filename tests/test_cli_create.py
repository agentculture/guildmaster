"""Tests for ``guild create`` — template-instantiate provisioning verb (t-create).

All external side-effects (gh, git, socket) are either monkeypatched away
(dry-run tests) or replaced with a fake runner (apply tests).  No real network,
no real GitHub, no real git.  No absolute paths hardcoded — all paths are
derived from tmp_path or Path(__file__).
"""

from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

import pytest

from guild.cli import main
from guild.cli._commands._provision_template import RunResult
from guild.cli._errors import GuildError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _never_called(*args, **kwargs):
    """Replacement for subprocess.run / socket.getaddrinfo that must not be called."""
    raise AssertionError("unexpected external call in dry-run")


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

_CULTURE = "agents:\n- suffix: guildmaster\n  backend: claude\n"
_LEDGER = """\
# Skill sources

| Skill | Upstream | Downstream copies (known) |
|-------|----------|--------------------------|
| `cicd` | `guildmaster` | `steward` |
| `communicate` | `guildmaster` | `steward` |
"""


def _seed(tmp_path: Path) -> Path:
    """Minimal guildmaster-like tree."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "culture.yaml").write_text(_CULTURE)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - 2026-01-01\n- init\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skill-sources.md").write_text(_LEDGER)
    for skill in ("cicd", "communicate"):
        d = tmp_path / ".claude" / "skills" / skill
        (d / "scripts").mkdir(parents=True)
        (d / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: the {skill} skill\ntype: command\n---\n"
        )
    # configure-repo.sh must exist for the apply tests to not skip step 5.
    cfg_dir = tmp_path / ".claude" / "skills" / "guild" / "scripts"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "configure-repo.sh").write_text("#!/usr/bin/env bash\necho 'configured'\n")
    return tmp_path


# ---------------------------------------------------------------------------
# Dry-run tests — zero external side-effects
# ---------------------------------------------------------------------------


def test_create_dry_run_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    # Block all subprocess/network so a stray call raises immediately.
    monkeypatch.setattr(subprocess, "run", _never_called)
    monkeypatch.setattr(socket, "getaddrinfo", _never_called)

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling.", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)

    assert out["dry_run"] is True
    assert out["agent"] == "agentculture/newsib"
    assert out["backend"] == "claude"
    assert out["template"] == "agentculture/culture-agent-template"
    assert "newsib" in out["clone_dest"]
    # Plan must expose rename map and steps.
    plan = out["plan"]
    assert plan["pkg"] == "newsib"
    assert plan["repo_token"] == "newsib"
    assert "culture_agent_template" in plan["rename_map"]
    assert "culture-agent-template" in plan["rename_map"]
    assert len(plan["steps"]) >= 5


def test_create_dry_run_human(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    monkeypatch.setattr(subprocess, "run", _never_called)

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling."])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "newsib" in out
    assert "rename map" in out.lower() or "rename" in out.lower()


def test_create_dry_run_ledger_diff_present(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    monkeypatch.setattr(subprocess, "run", _never_called)

    rc = main(["create", "--agent", "newsib", "--desc", "New agent.", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    # ledger_diff must mention the new agent.
    assert "newsib" in out["ledger_diff"]


def test_create_dry_run_no_writes_outside_devague(tmp_path, monkeypatch):
    """Dry-run must not write to any file in the tree."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    monkeypatch.setattr(subprocess, "run", _never_called)

    # Snapshot the tree before
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    rc = main(["create", "--agent", "newsib", "--desc", "No-write test."])
    assert rc == 0

    after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert before == after, "Dry-run must not write any files"


def test_create_dry_run_custom_template(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    monkeypatch.setattr(subprocess, "run", _never_called)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Desc.",
            "--template",
            "myorg/my-template",
            "--json",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["template"] == "myorg/my-template"


def test_create_dry_run_bare_agent_gets_org(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    monkeypatch.setattr(subprocess, "run", _never_called)

    rc = main(["create", "--agent", "bareonly", "--desc", "bare test", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["agent"] == "agentculture/bareonly"


def test_create_dry_run_explicit_owner_not_prefixed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(_seed(tmp_path))

    monkeypatch.setattr(subprocess, "run", _never_called)

    rc = main(["create", "--agent", "myorg/my-agent", "--desc", "explicit owner", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["agent"] == "myorg/my-agent"


# ---------------------------------------------------------------------------
# Apply tests — fake runner drives the exact command sequence
# ---------------------------------------------------------------------------


class _FakeRunner:
    """Records every command issued, returns configurable per-command results."""

    def __init__(self, *, repo_exists: bool = False, auth_ok: bool = True):
        self.calls: list[tuple[list[str], dict]] = []
        self._repo_exists = repo_exists
        self._auth_ok = auth_ok

    def __call__(self, cmd: list[str], *, cwd: str | None = None) -> RunResult:
        self.calls.append((list(cmd), {"cwd": cwd}))
        argv = cmd

        # gh auth status
        if argv[:3] == ["gh", "auth", "status"]:
            return RunResult(returncode=0 if self._auth_ok else 1)

        # gh repo view
        if argv[:3] == ["gh", "repo", "view"]:
            return RunResult(returncode=0 if self._repo_exists else 1)

        # gh api repos/<agent>/commits — the template-populate poll.
        if argv[:2] == ["gh", "api"] and len(argv) > 2 and argv[2].endswith("/commits"):
            return RunResult(returncode=0, stdout="1\n")

        # gh repo create (template)
        if argv[:2] == ["gh", "repo"] and "create" in argv:
            return RunResult(returncode=0, stdout="https://github.com/agentculture/newsib\n")

        # git clone
        if argv[:2] == ["git", "clone"]:
            # Materialise a fake clone destination so the transform can run.
            clone_dest = Path(argv[-1])
            clone_dest.mkdir(parents=True, exist_ok=True)
            # Minimal template tree so transform_clone doesn't fail.
            (clone_dest / "culture_agent_template").mkdir()
            (clone_dest / "culture_agent_template" / "__init__.py").write_text(
                "# culture_agent_template\n"
            )
            (clone_dest / "pyproject.toml").write_text(
                '[project]\nname = "culture-agent-template"\ndescription = "Template desc."\n'
            )
            (clone_dest / "culture.yaml").write_text(
                "agents:\n- suffix: culture-agent-template\n  backend: claude\n"
            )
            (clone_dest / "CLAUDE.md").write_text("# CLAUDE.md\nTemplate.\n")
            (clone_dest / "README.md").write_text(
                "# culture-agent-template\n\nA clonable template.\n"
            )
            return RunResult(returncode=0)

        # configure-repo.sh
        if "configure-repo.sh" in " ".join(str(a) for a in argv):
            return RunResult(returncode=0)

        # git -C ... add / commit / push
        if argv[:1] == ["git"] and "-C" in argv:
            return RunResult(returncode=0)

        return RunResult(returncode=0)


def test_create_apply_full_command_sequence(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner()

    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "A new sibling.",
            "--workspace-root",
            str(workspace),
            "--apply",
        ]
    )
    assert rc == 0

    issued = [" ".join(str(a) for a in c[0]) for c in runner.calls]

    # Auth check first.
    assert any("gh auth status" in c for c in issued), f"gh auth status missing from {issued}"
    # Existence check.
    assert any("gh repo view agentculture/newsib" in c for c in issued)
    # Template create.
    assert any("gh repo create agentculture/newsib" in c and "--template" in c for c in issued)
    # Clone.
    assert any("git clone" in c and "newsib" in c for c in issued)
    # configure-repo.sh
    assert any("configure-repo.sh" in c for c in issued)
    # git add / commit / push.
    assert any("git" in c and "add" in c for c in issued)
    assert any("git" in c and "commit" in c for c in issued)
    assert any("git" in c and "push" in c for c in issued)

    # Regression: the genesis push MUST come before configure-repo.sh applies the
    # "Protect main" ruleset (which requires PRs) — else the push is rejected.
    push_idx = next(i for i, c in enumerate(issued) if "git" in c and "push" in c)
    cfg_idx = next(i for i, c in enumerate(issued) if "configure-repo.sh" in c)
    assert push_idx < cfg_idx, f"push must precede configure-repo.sh; got {issued}"

    # Regression: the template-populate poll must run BEFORE the clone (gh copies
    # the template asynchronously; cloning an empty repo loses all content).
    poll_idx = next(i for i, c in enumerate(issued) if "gh api" in c and "/commits" in c)
    clone_idx = next(i for i, c in enumerate(issued) if "git clone" in c)
    assert poll_idx < clone_idx, f"populate-poll must precede clone; got {issued}"


def test_wait_for_template_polls_until_populated():
    """The repo is empty (409) for a few polls, then the template lands."""
    import guild.cli._commands._provision_template as _prov

    n = {"calls": 0}

    def runner(cmd, *, cwd=None):
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/commits"):
            n["calls"] += 1
            if n["calls"] < 3:
                return RunResult(returncode=1, stdout="", stderr="Git Repository is empty")
            return RunResult(returncode=0, stdout="1\n")
        return RunResult(returncode=0)

    _prov._wait_for_template("agentculture/x", runner, attempts=5, delay=0)
    assert n["calls"] == 3  # polled until the initial commit appeared


def test_wait_for_template_times_out():
    """Never populated → GuildError after exhausting attempts (no hang: delay=0)."""
    import guild.cli._commands._provision_template as _prov

    def runner(cmd, *, cwd=None):
        return RunResult(returncode=1, stdout="", stderr="empty")

    with pytest.raises(GuildError):
        _prov._wait_for_template("agentculture/x", runner, attempts=3, delay=0)


def test_create_apply_json_result(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "A new sibling.",
            "--workspace-root",
            str(workspace),
            "--apply",
            "--json",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["applied"] is True
    assert out["agent"] == "agentculture/newsib"
    assert out["pushed"] is True


def test_create_apply_registers_ledger(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Ledger test.",
            "--workspace-root",
            str(workspace),
            "--apply",
        ]
    )
    assert rc == 0
    ledger = (root / "docs" / "skill-sources.md").read_text()
    assert "`newsib`" in ledger


def test_create_apply_ledger_idempotent(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    workspace1 = tmp_path / "ws1"
    workspace1.mkdir()
    workspace2 = tmp_path / "ws2"
    workspace2.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "First.",
            "--workspace-root",
            str(workspace1),
            "--apply",
        ]
    )
    first = (root / "docs" / "skill-sources.md").read_text()

    runner2 = _FakeRunner()
    monkeypatch.setattr(_prov, "default_runner", runner2)
    main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Second.",
            "--workspace-root",
            str(workspace2),
            "--apply",
        ]
    )
    second = (root / "docs" / "skill-sources.md").read_text()

    assert first == second


def test_create_apply_does_not_use_real_ledger_path(tmp_path, monkeypatch):
    """Ledger writes must go to tmp_path, never the real docs/skill-sources.md."""
    real_ledger = Path(__file__).resolve().parents[1] / "docs" / "skill-sources.md"
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    if real_ledger.exists():
        before = real_ledger.read_text()

    main(["create", "--agent", "ledgertest", "--desc", "Should not touch real ledger.", "--apply"])

    if real_ledger.exists():
        assert real_ledger.read_text() == before


# ---------------------------------------------------------------------------
# Preflight fail-fast tests
# ---------------------------------------------------------------------------


def test_create_apply_fails_fast_when_repo_exists(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner(repo_exists=True)
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Already exists.",
            "--workspace-root",
            str(workspace),
            "--apply",
        ]
    )
    assert rc != 0

    issued = [" ".join(str(a) for a in c[0]) for c in runner.calls]
    # Must not issue create/clone/commit/push after the failure.
    assert not any("gh repo create" in c for c in issued)
    assert not any("git clone" in c for c in issued)
    assert not any("git commit" in c for c in issued)
    assert not any("git push" in c for c in issued)


def test_create_apply_fails_fast_when_gh_not_authed(tmp_path, monkeypatch, capsys):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner(auth_ok=False)
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "No auth.",
            "--workspace-root",
            str(workspace),
            "--apply",
        ]
    )
    assert rc != 0

    issued = [" ".join(str(a) for a in c[0]) for c in runner.calls]
    assert not any("gh repo create" in c for c in issued)


def test_create_apply_fails_fast_when_clone_dest_nonempty(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    # Pre-create a non-empty clone destination inside workspace.
    clone_dest = workspace / "newsib"
    clone_dest.mkdir(parents=True)
    (clone_dest / "existing_file.txt").write_text("I was here first.")

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Dest occupied.",
            "--apply",
            "--workspace-root",
            str(workspace),
        ]
    )
    assert rc != 0

    issued = [" ".join(str(a) for a in c[0]) for c in runner.calls]
    assert not any("gh repo create" in c for c in issued)


def test_create_apply_fails_fast_when_clone_dest_is_a_file(tmp_path, monkeypatch):
    """A file/symlink at the destination must be rejected BEFORE the repo is
    created (else apply makes the remote, then git clone fails → partial)."""
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    # Pre-create the clone destination as a FILE (not a dir).
    (workspace / "newsib").write_text("I am a file, not a directory.")

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    rc = main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "File at dest.",
            "--apply",
            "--workspace-root",
            str(workspace),
        ]
    )
    assert rc != 0
    issued = [" ".join(str(a) for a in c[0]) for c in runner.calls]
    assert not any("gh repo create" in c for c in issued)  # no remote side-effect


def test_create_rejects_invalid_package_name(tmp_path, monkeypatch, capsys):
    """A repo name that derives an invalid Python identifier fails fast."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(subprocess, "run", _never_called)

    # "2fa.tool" -> pkg "2fa.tool": not a valid identifier (dot + leading digit).
    rc = main(["create", "--agent", "2fa.tool", "--desc", "bad name"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "invalid Python package name" in err


# ---------------------------------------------------------------------------
# Transform is invoked on the cloned tree
# ---------------------------------------------------------------------------


def test_create_apply_transform_renames_in_clone(tmp_path, monkeypatch):
    root = _seed(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.chdir(root)

    runner = _FakeRunner()
    import guild.cli._commands._provision_template as _prov

    monkeypatch.setattr(_prov, "default_runner", runner)

    main(
        [
            "create",
            "--agent",
            "newsib",
            "--desc",
            "Transform test.",
            "--workspace-root",
            str(workspace),
            "--apply",
        ]
    )

    clone_dest = workspace / "newsib"
    # Package dir should be renamed.
    assert (clone_dest / "newsib").is_dir()
    assert not (clone_dest / "culture_agent_template").exists()
    # CLAUDE.md seed should name the agent.
    claude_md = (clone_dest / "CLAUDE.md").read_text()
    assert "newsib" in claude_md
    assert "/init" in claude_md
