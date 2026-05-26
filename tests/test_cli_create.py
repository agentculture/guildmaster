"""Tests for ``guild create`` — dry-run default, --apply, ledger idempotency (t7).

Acceptance criteria verified:
  AC1 — dry-run default: renders ProvisionPlan, exits 0, _provision.apply NOT called.
        --json emits a structured JSON payload. --apply calls _provision.apply
        (stubbed — no real network) then registers agent in ledger.
  AC2 — ``create`` is registered in argparse and in VERBS.
  AC3 — dry-run-external-free, apply-calls-executor, ledger-idempotency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guild.cli import main
from guild.cli._commands import VERBS, _provision

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_CULTURE = "agents:\n- suffix: guildmaster\n  backend: claude\n"

# Ledger with a Downstream column so register_consumer produces a diff.
_LEDGER = """\
# Skill sources

| Skill | Upstream | Downstream copies |
|-------|----------|-------------------|
| `cicd` | `steward` | — |
| `run-tests` | `steward` | — |
"""

_APPLY_RESULT = {
    "applied": True,
    "repo": "agentculture/newsib",
    "clone_dest": "/tmp/newsib",
    "manifest_files": 5,
    "kit_files": 3,
    "pushed": True,
}


def _seed(tmp_path: Path) -> Path:
    """Populate tmp_path as a minimal guildmaster-like repo root."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "culture.yaml").write_text(_CULTURE)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - 2026-01-01\n- init\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skill-sources.md").write_text(_LEDGER)
    for skill in ("cicd", "run-tests"):
        d = tmp_path / ".claude" / "skills" / skill
        (d / "scripts").mkdir(parents=True)
        (d / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (d / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: the {skill} skill\ntype: command\n---\n"
        )
    return tmp_path


# ---------------------------------------------------------------------------
# AC2 — create is registered in VERBS and argparse
# ---------------------------------------------------------------------------


def test_create_in_verbs():
    """``create`` must appear in the VERBS dict."""
    assert "create" in VERBS


def test_create_registered_in_argparse(tmp_path, monkeypatch):
    """Calling ``guild create --help`` must not raise SystemExit with code != 0."""
    monkeypatch.chdir(_seed(tmp_path))
    with pytest.raises(SystemExit) as exc_info:
        main(["create", "--help"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# AC1 / AC3 — dry-run default: no external calls, exit 0, plan rendered
# ---------------------------------------------------------------------------


def test_dry_run_default_exit_zero_no_apply(tmp_path, monkeypatch, capsys):
    """Dry-run must render the plan, exit 0, and NOT call _provision.apply."""
    monkeypatch.chdir(_seed(tmp_path))

    apply_called = []

    def _fake_apply(*a, **k):
        apply_called.append(True)
        return _APPLY_RESULT

    monkeypatch.setattr(_provision, "apply", _fake_apply)

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling"])
    assert rc == 0
    assert not apply_called, "_provision.apply must NOT be called during dry-run"
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "newsib" in out


def test_dry_run_human_output_contains_plan_sections(tmp_path, monkeypatch, capsys):
    """Dry-run human output must mention repo_spec fields and kit/ledger sections."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    rc = main(["create", "--agent", "newsib", "--desc", "Test agent"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "newsib" in out
    assert "Test agent" in out
    # Plan rendering includes scaffold manifest + kit + ledger sections.
    assert "manifest" in out.lower() or "scaffold" in out.lower() or "files" in out.lower()


def test_dry_run_json_flag_emits_structured_payload(tmp_path, monkeypatch, capsys):
    """``--json`` in dry-run must emit a JSON object with the plan fields."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["repo_spec"]["agent"] == "agentculture/newsib"
    assert payload["repo_spec"]["desc"] == "A new sibling"
    assert isinstance(payload["kit_dests"], list)
    assert isinstance(payload["manifest"], dict)


def test_dry_run_does_not_modify_ledger(tmp_path, monkeypatch):
    """Dry-run must leave docs/skill-sources.md byte-for-byte unchanged."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    original = (root / "docs" / "skill-sources.md").read_text()
    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling"])
    assert rc == 0
    after = (root / "docs" / "skill-sources.md").read_text()
    assert original == after, "dry-run must not write to the ledger"


# ---------------------------------------------------------------------------
# AC1 / AC3 — --apply path: calls executor, registers in ledger
# ---------------------------------------------------------------------------


def test_apply_calls_provision_apply(tmp_path, monkeypatch, capsys):
    """``--apply`` must call _provision.apply exactly once."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    calls = []

    def _fake_apply(plan, **kw):
        calls.append(plan)
        return {
            "applied": True,
            "repo": plan.repo_spec["agent"],
            "clone_dest": "/tmp/newsib",
            "manifest_files": 5,
            "kit_files": 3,
            "pushed": True,
        }

    monkeypatch.setattr(_provision, "apply", _fake_apply)
    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply"])
    assert rc == 0
    assert len(calls) == 1, "_provision.apply should be called exactly once"
    assert calls[0].repo_spec["agent"] == "agentculture/newsib"


def test_apply_registers_agent_in_ledger(tmp_path, monkeypatch, capsys):
    """``--apply`` must write the agent into docs/skill-sources.md."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    monkeypatch.setattr(
        _provision,
        "apply",
        lambda plan, **kw: {
            "applied": True,
            "repo": plan.repo_spec["agent"],
            "clone_dest": "/tmp/newsib",
            "manifest_files": 5,
            "kit_files": 3,
            "pushed": True,
        },
    )

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply"])
    assert rc == 0
    ledger = (root / "docs" / "skill-sources.md").read_text()
    assert "`newsib`" in ledger


def test_apply_json_flag_emits_apply_result(tmp_path, monkeypatch, capsys):
    """``--apply --json`` must emit a structured payload with applied=True."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    monkeypatch.setattr(
        _provision,
        "apply",
        lambda plan, **kw: {
            "applied": True,
            "repo": plan.repo_spec["agent"],
            "clone_dest": "/tmp/newsib",
            "manifest_files": 5,
            "kit_files": 3,
            "pushed": True,
        },
    )

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is True
    assert payload["agent"] == "agentculture/newsib"
    assert payload["pushed"] is True
    assert "ledger_written" in payload


def test_apply_human_output_mentions_agent(tmp_path, monkeypatch, capsys):
    """``--apply`` human output must confirm the agent was created."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    monkeypatch.setattr(
        _provision,
        "apply",
        lambda plan, **kw: {
            "applied": True,
            "repo": plan.repo_spec["agent"],
            "clone_dest": "/tmp/newsib",
            "manifest_files": 5,
            "kit_files": 3,
            "pushed": True,
        },
    )

    rc = main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "newsib" in out or "agentculture/newsib" in out


# ---------------------------------------------------------------------------
# AC3 — ledger idempotency: two --apply runs leave exactly ONE consumer entry
# ---------------------------------------------------------------------------


def test_apply_ledger_idempotent(tmp_path, monkeypatch):
    """Two consecutive --apply runs must not duplicate the consumer entry."""
    root = _seed(tmp_path)
    monkeypatch.chdir(root)

    monkeypatch.setattr(
        _provision,
        "apply",
        lambda plan, **kw: {
            "applied": True,
            "repo": plan.repo_spec["agent"],
            "clone_dest": "/tmp/newsib",
            "manifest_files": 5,
            "kit_files": 3,
            "pushed": True,
        },
    )

    main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply"])
    first = (root / "docs" / "skill-sources.md").read_text()

    main(["create", "--agent", "newsib", "--desc", "A new sibling", "--apply"])
    second = (root / "docs" / "skill-sources.md").read_text()

    assert first == second, "second apply must not change the ledger (idempotency)"
    # newsib appears exactly once per skill row (two skill rows -> two occurrences total).
    skill_rows = [
        ln for ln in first.splitlines() if ln.strip().startswith("|") and "`newsib`" in ln
    ]
    for row in skill_rows:
        assert row.count("`newsib`") == 1, f"newsib duplicated in row: {row!r}"


# ---------------------------------------------------------------------------
# AC1 — bare agent name gets org prefix
# ---------------------------------------------------------------------------


def test_bare_agent_name_gets_org_prefix(tmp_path, monkeypatch, capsys):
    """A bare ``--agent name`` must be normalised to ``agentculture/name``."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    rc = main(["create", "--agent", "mynewagent", "--desc", "desc", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_spec"]["agent"] == "agentculture/mynewagent"


def test_explicit_org_slash_repo_preserved(tmp_path, monkeypatch, capsys):
    """An explicit ``owner/repo`` form must pass through unchanged."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    rc = main(["create", "--agent", "myorg/myrepo", "--desc", "desc", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_spec"]["agent"] == "myorg/myrepo"


# ---------------------------------------------------------------------------
# AC1 — backend option is threaded through
# ---------------------------------------------------------------------------


def test_backend_acp_threaded_into_plan(tmp_path, monkeypatch, capsys):
    """``--backend acp`` must appear in the dry-run JSON payload."""
    monkeypatch.chdir(_seed(tmp_path))
    monkeypatch.setattr(_provision, "apply", lambda *a, **k: _APPLY_RESULT)

    rc = main(["create", "--agent", "newsib", "--desc", "desc", "--backend", "acp", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_spec"]["backend"] == "acp"
