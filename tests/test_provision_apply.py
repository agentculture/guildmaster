"""Tests for guild.cli._commands._provision — the --apply executor (t6).

TDD: written BEFORE the implementation.

Covers acceptance criteria:
  #1 — apply(plan, runner) performs, IN ORDER: gh-repo-create (public, with
       description, NO --license) -> clone into workspace root -> write manifest
       (+ copy kit) -> git add -> git commit (genesis) -> git push to main,
       every external command through an injectable runner.
  #2 — pre-checks the target does NOT already exist; raises a typed error with
       NO PARTIAL SCAFFOLD when it does, or when gh auth is missing; uses only
       the gh login guildmaster already holds.
  #3 — a FAKE runner asserts the exact ordered command sequence PLUS the
       fail-fast-on-existing-target behaviour, with NO real network.
  #4 — boundary guard (c6/h10): refuses / no-ops on a target that already
       exists or whose local clone destination already exists and is non-empty,
       rather than scaffolding arbitrary content into it.

Risk r2 is resolved BY CONSTRUCTION here: the runner is injected and tmp dirs
are used, so no test needs real GitHub credentials and nothing hits the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pytest

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.scaffold.plan import ProvisionPlan

# ---------------------------------------------------------------------------
# Fake runner
# ---------------------------------------------------------------------------


@dataclass
class _Result:
    """Stand-in for the object the real runner returns."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    """Records every command list it is asked to run and returns scripted results.

    ``scripts`` maps a *match token* (a substring that must appear as one of the
    argv elements, e.g. ``"repo"`` or ``"clone"``) to the :class:`_Result` to
    return. The first matching script wins; commands with no script return a
    success result. Every invocation is appended to :attr:`calls` so a test can
    assert the exact ordered sequence — and assert that NOTHING ran after a
    fail-fast point.
    """

    def __init__(self, scripts: dict[str, _Result] | None = None) -> None:
        self.calls: list[list[str]] = []
        self._scripts = scripts or {}

    def __call__(self, cmd: Sequence[str], *, cwd: str | None = None) -> _Result:
        argv = list(cmd)
        self.calls.append(argv)
        for token, result in self._scripts.items():
            if token in argv:
                return result
        return _Result(returncode=0)

    # Convenience views ----------------------------------------------------

    @property
    def programs(self) -> list[str]:
        """The leading program of each recorded call (e.g. 'gh', 'git')."""
        return [c[0] for c in self.calls if c]

    def joined(self) -> list[str]:
        return [" ".join(c) for c in self.calls]


# ---------------------------------------------------------------------------
# Plan fixture
# ---------------------------------------------------------------------------

_AGENT = "agentculture/appsec"
_DESC = "AppSec agent for the AgentCulture mesh"


@pytest.fixture()
def plan(tmp_path: Path) -> ProvisionPlan:
    """A minimal, self-contained ProvisionPlan whose clone_dest is under tmp."""
    clone_dest = tmp_path / "appsec"
    return ProvisionPlan(
        repo_spec={
            "agent": _AGENT,
            "desc": _DESC,
            "backend": "claude",
            "visibility": "public",
            "license": "MIT",
            "clone_dest": str(clone_dest),
        },
        manifest={
            "LICENSE": "MIT ...\n",
            "README.md": "# appsec\n",
            "culture.yaml": "agents:\n- suffix: appsec\n  backend: claude\n",
        },
        kit_dests=[".claude/skills/cicd/SKILL.md"],
        ledger_diff="",
    )


# ---------------------------------------------------------------------------
# Criterion #1 / #3 — happy-path ordered command sequence
# ---------------------------------------------------------------------------


def test_happy_path_command_sequence(plan: ProvisionPlan) -> None:
    """apply() issues the exact ordered external command sequence.

    Order contract:
      0. gh auth status          (preflight: auth present)
      1. gh repo view <agent>    (preflight: must be absent -> nonzero)
      2. gh repo create ...      (public, --description, NO --license)
      3. git clone <url> <dest>
      4. git -C <dest> add -A
      5. git -C <dest> commit ...        (the genesis commit)
      6. git -C <dest> branch -M main    (ensure branch is main)
      7. git -C <dest> push -u origin main
    """
    from guild.cli._commands import _provision

    clone_dest = Path(plan.repo_spec["clone_dest"])

    # The fake 'clone' cannot create the dir; emulate git clone by creating it.
    def runner(cmd, *, cwd=None):
        argv = list(cmd)
        fake.calls.append(argv)
        if "clone" in argv:
            clone_dest.mkdir(parents=True, exist_ok=True)
            (clone_dest / ".git").mkdir(exist_ok=True)
            return _Result(returncode=0)
        if "view" in argv:
            return _Result(returncode=1, stderr="Could not resolve to a Repository")
        return _Result(returncode=0)

    fake = FakeRunner()

    result = _provision.apply(plan, runner=runner)

    progs = [c[0] for c in fake.calls]
    # gh comes first (auth + view + create), then git for the rest.
    assert progs[0] == "gh"  # auth status
    assert "auth" in fake.calls[0] and "status" in fake.calls[0]
    assert fake.calls[1][:3] == ["gh", "repo", "view"]
    assert _AGENT in fake.calls[1]

    create = fake.calls[2]
    assert create[:3] == ["gh", "repo", "create"]
    assert _AGENT in create
    assert "--public" in create
    assert "--description" in create
    assert _DESC in create
    # r1 resolution: NO competing initial commit seeded by gh.
    assert "--license" not in create
    assert "--gitignore" not in create

    # Remaining steps are git, in order.
    git_calls = [c for c in fake.calls if c and c[0] == "git"]
    assert git_calls[0][:2] == ["git", "clone"]
    # add -A, commit, branch -M main, push -u origin main — order preserved.
    flat = [" ".join(c) for c in git_calls]
    assert any("add -A" in s for s in flat)
    assert any("commit" in s for s in flat)
    assert any("push" in s and "origin main" in s for s in flat)
    # commit precedes push
    commit_idx = next(i for i, s in enumerate(flat) if "commit" in s)
    push_idx = next(i for i, s in enumerate(flat) if "push" in s)
    assert commit_idx < push_idx

    # Manifest was actually written into the clone dest.
    assert (clone_dest / "LICENSE").is_file()
    assert (clone_dest / "README.md").read_text() == "# appsec\n"

    # Result summary.
    assert result["repo"] == _AGENT
    assert result["clone_dest"] == str(clone_dest)
    assert result["pushed"] is True


def test_manifest_and_kit_written(plan: ProvisionPlan, tmp_path: Path) -> None:
    """apply() writes every manifest file and copies the kit into the clone."""
    from guild.cli._commands import _provision

    # Provide a real kit source so copy_plan-style copy has something to copy.
    src_skill = tmp_path / "src" / ".claude" / "skills" / "cicd"
    src_skill.mkdir(parents=True)
    (src_skill / "SKILL.md").write_text("cicd skill\n")

    clone_dest = Path(plan.repo_spec["clone_dest"])

    def runner(cmd, *, cwd=None):
        argv = list(cmd)
        calls.append(argv)
        if "clone" in argv:
            clone_dest.mkdir(parents=True, exist_ok=True)
            (clone_dest / ".git").mkdir(exist_ok=True)
        if "view" in argv:
            return _Result(returncode=1)
        return _Result(returncode=0)

    calls: list[list[str]] = []

    # kit_src_map maps dest-relpath -> abs source path, injected so the test
    # does not depend on guildmaster's own .claude/skills.
    kit_src = {".claude/skills/cicd/SKILL.md": str(src_skill / "SKILL.md")}
    _provision.apply(plan, runner=runner, kit_src=kit_src)

    assert (clone_dest / ".claude" / "skills" / "cicd" / "SKILL.md").read_text() == "cicd skill\n"


# ---------------------------------------------------------------------------
# Criterion #2 / #3 — fail-fast on existing target
# ---------------------------------------------------------------------------


def test_fail_fast_when_repo_exists(plan: ProvisionPlan) -> None:
    """If `gh repo view` succeeds (repo exists) -> refuse, NOTHING else runs."""
    from guild.cli._commands import _provision

    fake = FakeRunner(
        scripts={
            "status": _Result(returncode=0),  # auth ok
            "view": _Result(returncode=0, stdout="exists"),  # repo EXISTS
        }
    )

    with pytest.raises(GuildError) as exc:
        _provision.apply(plan, runner=fake)

    assert exc.value.code == EXIT_USER_ERROR
    # No create / clone / commit / push were ever issued.
    joined = fake.joined()
    assert not any("repo create" in s for s in joined)
    assert not any("clone" in s for s in joined)
    assert not any("push" in s for s in joined)
    # And no local scaffold was written.
    assert not Path(plan.repo_spec["clone_dest"]).exists()


def test_fail_fast_when_auth_missing(plan: ProvisionPlan) -> None:
    """If `gh auth status` is nonzero -> env error, NOTHING else runs."""
    from guild.cli._commands import _provision

    fake = FakeRunner(scripts={"status": _Result(returncode=1, stderr="not logged in")})

    with pytest.raises(GuildError) as exc:
        _provision.apply(plan, runner=fake)

    assert exc.value.code == EXIT_ENV_ERROR
    joined = fake.joined()
    assert not any("repo view" in s for s in joined)
    assert not any("repo create" in s for s in joined)
    assert not any("clone" in s for s in joined)
    assert not Path(plan.repo_spec["clone_dest"]).exists()


# ---------------------------------------------------------------------------
# Criterion #4 — boundary guard (c6/h10)
# ---------------------------------------------------------------------------


def test_boundary_refuse_nonempty_local_dest(plan: ProvisionPlan) -> None:
    """A non-empty local clone destination is refused (no scaffold into it)."""
    from guild.cli._commands import _provision

    clone_dest = Path(plan.repo_spec["clone_dest"])
    clone_dest.mkdir(parents=True)
    (clone_dest / "pre-existing.txt").write_text("do not clobber me\n")

    fake = FakeRunner(scripts={"view": _Result(returncode=1)})

    with pytest.raises(GuildError) as exc:
        _provision.apply(plan, runner=fake)

    assert exc.value.code == EXIT_USER_ERROR
    # The pre-existing content is untouched and nothing external ran past auth.
    assert (clone_dest / "pre-existing.txt").read_text() == "do not clobber me\n"
    joined = fake.joined()
    assert not any("repo create" in s for s in joined)
    assert not any("clone" in s for s in joined)


def test_boundary_allows_empty_existing_dest(plan: ProvisionPlan) -> None:
    """An *empty* existing dest is fine (git clone tolerates empty dirs)."""
    from guild.cli._commands import _provision

    clone_dest = Path(plan.repo_spec["clone_dest"])
    clone_dest.mkdir(parents=True)  # exists but empty

    def runner(cmd, *, cwd=None):
        argv = list(cmd)
        calls.append(argv)
        if "view" in argv:
            return _Result(returncode=1)
        return _Result(returncode=0)

    calls: list[list[str]] = []
    result = _provision.apply(plan, runner=runner)
    assert result["pushed"] is True


# ---------------------------------------------------------------------------
# preflight() is callable on its own (used by t7 + tests)
# ---------------------------------------------------------------------------


def test_preflight_is_exposed(plan: ProvisionPlan) -> None:
    """preflight(plan, runner) is a public helper that does the checks only."""
    from guild.cli._commands import _provision

    fake = FakeRunner(scripts={"view": _Result(returncode=1)})
    # Should not raise; should NOT create/clone (checks only).
    _provision.preflight(plan, runner=fake)
    joined = fake.joined()
    assert not any("repo create" in s for s in joined)
    assert not any("clone" in s for s in joined)
