"""Tests for guild.scaffold.plan — ProvisionPlan dry-run surface (t5).

TDD: written BEFORE the implementation.

Covers:
  criterion #1 — build() composes manifest+kit+identity+ledger-diff into a
                  ProvisionPlan dataclass; render_human() and to_dict() work.
  criterion #2 — building and rendering the plan performs zero subprocess calls,
                  zero network, and zero file writes outside .devague.
"""

from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_AGENT = "agentculture/appsec"
_DESC = "AppSec agent for the AgentCulture mesh"
_BACKEND = "claude"

# The guildmaster repo root, resolved portably from this test file's location
# (tests/ -> repo root). Never hardcode an absolute worktree/home path: it
# breaks in any other checkout and trips steward doctor's portability invariant.
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_plan(**kw):
    """Import and call plan.build with sensible defaults."""
    from guild.scaffold.plan import build

    defaults: dict[str, Any] = dict(
        agent=_AGENT,
        desc=_DESC,
        backend=_BACKEND,
        root=None,  # resolved inside fixture-based tests
        workspace_root=None,
    )
    defaults.update(kw)
    return build(**defaults)


# ---------------------------------------------------------------------------
# Criterion #1 — ProvisionPlan shape and rendering
# ---------------------------------------------------------------------------


class TestProvisionPlanImport:
    """The plan module and ProvisionPlan can be imported."""

    def test_import_build(self) -> None:
        from guild.scaffold.plan import build  # noqa: F401 (import smoke)

    def test_import_provision_plan(self) -> None:
        from guild.scaffold.plan import ProvisionPlan  # noqa: F401


class TestProvisionPlanFields:
    """ProvisionPlan dataclass has the expected fields."""

    def test_has_repo_spec(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert hasattr(plan, "repo_spec")

    def test_has_manifest(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert hasattr(plan, "manifest")

    def test_has_kit_dests(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert hasattr(plan, "kit_dests")

    def test_has_ledger_diff(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert hasattr(plan, "ledger_diff")


class TestRepoSpec:
    """repo_spec carries the expected metadata."""

    def test_repo_spec_contains_agent(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert plan.repo_spec["agent"] == _AGENT

    def test_repo_spec_contains_desc(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert plan.repo_spec["desc"] == _DESC

    def test_repo_spec_contains_backend(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert plan.repo_spec["backend"] == _BACKEND

    def test_repo_spec_visibility_is_public(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert plan.repo_spec["visibility"] == "public"

    def test_repo_spec_license_is_mit(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert plan.repo_spec["license"] == "MIT"

    def test_repo_spec_clone_dest_ends_with_repo_name(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        # clone_dest should be workspace_root / "appsec"
        clone_dest = Path(plan.repo_spec["clone_dest"])
        assert clone_dest.name == "appsec"
        assert clone_dest.parent == tmp_path


class TestManifest:
    """manifest contains all expected scaffold + identity files."""

    def test_manifest_is_dict(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert isinstance(plan.manifest, dict)

    def test_manifest_has_scaffold_files(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        # From manifest.build
        assert "pyproject.toml" in plan.manifest
        assert "appsec/__init__.py" in plan.manifest

    def test_manifest_has_identity_files(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        # From identity.build
        assert "CLAUDE.md" in plan.manifest
        assert "culture.yaml" in plan.manifest
        assert ".claude/skills.local.yaml.example" in plan.manifest

    def test_manifest_identity_does_not_conflict_with_scaffold(self, tmp_path: Path) -> None:
        """No overlap — identity CLAUDE.md is distinct from scaffold files."""
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        # Identity adds CLAUDE.md; manifest.build does not produce it
        claude_md = plan.manifest.get("CLAUDE.md", "")
        assert _AGENT.rsplit("/", 1)[-1] in claude_md  # identity embedded agent name


class TestKitDests:
    """kit_dests lists the planned .claude/skills/ destination paths."""

    def test_kit_dests_is_list(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert isinstance(plan.kit_dests, list)

    def test_kit_dests_are_under_claude_skills(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        for dest in plan.kit_dests:
            assert dest.startswith(".claude/skills/"), f"Unexpected dest: {dest!r}"

    def test_kit_dests_nonempty(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert len(plan.kit_dests) > 0, "kit_dests should not be empty"

    def test_kit_dests_exclude_self_skills(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build
        from guild.skills import SELF_SKILLS

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        for dest in plan.kit_dests:
            # e.g. .claude/skills/teach/... — "teach" is a SELF_SKILL
            skill_name = dest.split("/")[2]  # .claude/skills/<name>/...
            assert skill_name not in SELF_SKILLS, f"Self-skill {skill_name!r} leaked into kit_dests"


class TestLedgerDiff:
    """ledger_diff is a string (may be empty if ledger has no Downstream column)."""

    def test_ledger_diff_is_string(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        assert isinstance(plan.ledger_diff, str)


class TestRenderHuman:
    """render_human() returns a non-empty, human-readable string."""

    def test_render_human_returns_str(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        rendered = plan.render_human()
        assert isinstance(rendered, str)

    def test_render_human_contains_agent(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        rendered = plan.render_human()
        assert "appsec" in rendered

    def test_render_human_shows_manifest_file_count(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        rendered = plan.render_human()
        # Should mention at minimum pyproject.toml or a file count
        assert "pyproject.toml" in rendered or str(len(plan.manifest)) in rendered

    def test_render_human_shows_kit_count_or_dest(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        rendered = plan.render_human()
        assert ".claude/skills" in rendered or str(len(plan.kit_dests)) in rendered

    def test_render_human_mentions_dry_run(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        rendered = plan.render_human()
        assert "dry" in rendered.lower() or "plan" in rendered.lower()


class TestToDict:
    """to_dict() returns a JSON-serialisable structure."""

    def test_to_dict_returns_dict(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        d = plan.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_is_json_serialisable(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        d = plan.to_dict()
        serialised = json.dumps(d)  # must not raise
        roundtrip = json.loads(serialised)
        assert roundtrip["repo_spec"]["agent"] == _AGENT

    def test_to_dict_contains_all_top_level_keys(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        d = plan.to_dict()
        for key in ("repo_spec", "manifest", "kit_dests", "ledger_diff"):
            assert key in d, f"Missing key in to_dict(): {key!r}"

    def test_to_dict_manifest_keys_are_relpaths(self, tmp_path: Path) -> None:
        from guild.scaffold.plan import build

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=_REPO_ROOT,
            workspace_root=tmp_path,
        )
        d = plan.to_dict()
        for k in d["manifest"]:
            # all keys should be relative paths (no leading /)
            assert not k.startswith("/"), f"Absolute path in manifest: {k!r}"


# ---------------------------------------------------------------------------
# Criterion #2 — ZERO external (subprocess, network, file writes)
# ---------------------------------------------------------------------------


class TestZeroExternal:
    """Building and rendering the ProvisionPlan must NOT:
    - invoke any subprocess (subprocess.run / Popen)
    - open any network connection (socket.socket)
    - write any files outside .devague
    """

    @pytest.fixture(autouse=True)
    def _patch_subprocess(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raise if any subprocess call is attempted."""

        def _raise_run(*args, **kwargs):
            raise AssertionError(
                f"subprocess.run was called during plan.build/render: args={args!r}"
            )

        def _raise_popen(*args, **kwargs):
            raise AssertionError(
                f"subprocess.Popen was called during plan.build/render: args={args!r}"
            )

        monkeypatch.setattr(subprocess, "run", _raise_run)
        monkeypatch.setattr(subprocess, "Popen", _raise_popen)

    @pytest.fixture(autouse=True)
    def _patch_socket(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raise if any socket is created (network prohibition)."""

        class _RaisingSocket:
            def __init__(self, *args, **kwargs):
                raise AssertionError(
                    "socket.socket was instantiated during plan.build/render — "
                    "no network calls allowed"
                )

        monkeypatch.setattr(socket, "socket", _RaisingSocket)

    def test_build_does_not_call_subprocess_or_network(self, tmp_path: Path) -> None:
        """build() completes with zero subprocess/network calls."""
        from guild.scaffold.plan import build

        root = _REPO_ROOT
        # Should not raise (the fixtures raise on any subprocess/socket use)
        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=root,
            workspace_root=tmp_path,
        )
        assert plan is not None

    def test_render_human_does_not_call_subprocess_or_network(self, tmp_path: Path) -> None:
        """render_human() completes with zero subprocess/network calls."""
        from guild.scaffold.plan import build

        root = _REPO_ROOT
        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=root,
            workspace_root=tmp_path,
        )
        result = plan.render_human()
        assert isinstance(result, str)

    def test_to_dict_does_not_call_subprocess_or_network(self, tmp_path: Path) -> None:
        """to_dict() completes with zero subprocess/network calls."""
        from guild.scaffold.plan import build

        root = _REPO_ROOT
        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=root,
            workspace_root=tmp_path,
        )
        d = plan.to_dict()
        assert isinstance(d, dict)

    def test_no_file_writes_outside_devague(self, tmp_path: Path) -> None:
        """build()+render_human()+to_dict() write nothing outside .devague."""
        from guild.scaffold.plan import build

        root = _REPO_ROOT
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()

        # Snapshot files before
        before = set(tmp_path.rglob("*"))

        plan = build(
            agent=_AGENT,
            desc=_DESC,
            backend=_BACKEND,
            root=root,
            workspace_root=workspace_root,
        )
        _ = plan.render_human()
        _ = plan.to_dict()

        # Snapshot files after
        after = set(tmp_path.rglob("*"))
        new_files = after - before

        # Any new file must be under .devague (tolerate pytest tmp artifacts)
        non_devague = [f for f in new_files if ".devague" not in str(f) and f.is_file()]
        assert non_devague == [], f"Unexpected files written outside .devague: {non_devague!r}"
