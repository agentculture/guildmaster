"""Tests for guild.scaffold.instantiate — the pure template transform (t-inst).

These tests work entirely against a fixture directory built in tmp_path; no
network, no subprocess, no real github.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from guild.scaffold.instantiate import (
    rename_map,
    transform_clone,
    transform_plan,
)

# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

_TEMPLATE_PKG = "culture_agent_template"
_TEMPLATE_REPO = "culture-agent-template"


def _build_fixture(tmp_path: Path) -> Path:
    """Build a minimal tree that mimics agentculture/culture-agent-template."""
    # .git sentinel (so .git files are skipped)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n\trepositoryformatversion = 0\n")

    # Package directory with __init__.py that imports from the package
    pkg_dir = tmp_path / _TEMPLATE_PKG
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        '"""culture_agent_template package."""\n'
        "from culture_agent_template import cli  # noqa: F401\n"
    )

    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "culture-agent-template"\n'
        'description = "A clonable AgentCulture agent template."\n'
        'packages = ["culture_agent_template"]\n'
        '\n[project.scripts]\nculture-agent-template = "culture_agent_template.cli:main"\n'
    )

    # culture.yaml
    (tmp_path / "culture.yaml").write_text(
        "agents:\n- suffix: culture-agent-template\n  backend: claude\n"
    )

    # sonar-project.properties
    (tmp_path / "sonar-project.properties").write_text(
        "sonar.projectKey=agentculture_culture-agent-template\n"
        "sonar.sources=culture_agent_template\n"
    )

    # CLAUDE.md — template's own "clonable template" prose
    (tmp_path / "CLAUDE.md").write_text(
        "# CLAUDE.md\n\nThis is the culture-agent-template.\n"
        "culture_agent_template is the Python package.\n"
    )

    # README.md
    (tmp_path / "README.md").write_text(
        "# culture-agent-template\n\nA clonable AgentCulture agent template.\n\nMore docs.\n"
    )

    # .claude/skills/cicd/SKILL.md — name in prose (but scripts contain NO name)
    cicd_dir = tmp_path / ".claude" / "skills" / "cicd"
    (cicd_dir / "scripts").mkdir(parents=True)
    (cicd_dir / "scripts" / "run.sh").write_text("#!/bin/sh\n# no name here\n")
    (cicd_dir / "SKILL.md").write_text(
        "---\nname: cicd\ndescription: CI/CD for culture-agent-template.\ntype: command\n---\n"
        "# cicd\n\nThis skill is vendored by culture-agent-template consumers.\n"
    )

    # .claude/skills.local.yaml.example — name appears in prose
    (tmp_path / ".claude" / "skills.local.yaml.example").write_text(
        "# Per-machine config for culture-agent-template.\n"
        "# Sibling paths:\n"
        "sibling_projects:\n"
        "  - ../guildmaster\n"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# rename_map tests
# ---------------------------------------------------------------------------


def test_rename_map_simple():
    m = rename_map("appsec")
    assert m["culture_agent_template"] == "appsec"
    assert m["culture-agent-template"] == "appsec"
    # Keys in insertion order: underscore first.
    assert list(m.keys()) == ["culture_agent_template", "culture-agent-template"]


def test_rename_map_hyphenated():
    m = rename_map("my-agent")
    assert m["culture_agent_template"] == "my_agent"
    assert m["culture-agent-template"] == "my-agent"


def test_rename_map_uppercase_lowercased():
    m = rename_map("MyAgent")
    assert m["culture_agent_template"] == "myagent"
    assert m["culture-agent-template"] == "myagent"


# ---------------------------------------------------------------------------
# transform_plan tests
# ---------------------------------------------------------------------------


def test_transform_plan_returns_expected_keys():
    plan = transform_plan("appsec", "Application security agent.")
    assert set(plan.keys()) >= {
        "bare",
        "pkg",
        "repo_token",
        "rename_map",
        "package_dir_rename",
        "pyproject_desc",
        "claude_md_seed_synopsis",
        "steps",
    }


def test_transform_plan_pkg_and_repo_token():
    plan = transform_plan("my-agent", "Does things.")
    assert plan["pkg"] == "my_agent"
    assert plan["repo_token"] == "my-agent"


def test_transform_plan_steps_describe_actions():
    plan = transform_plan("appsec", "AppSec scanner.")
    steps = "\n".join(plan["steps"])
    assert "culture_agent_template" in steps
    assert "culture-agent-template" in steps
    assert "pyproject" in steps
    assert "README" in steps
    assert "CLAUDE.md" in steps


# ---------------------------------------------------------------------------
# transform_clone tests — file-level assertions
# ---------------------------------------------------------------------------


def test_transform_renames_package_dir(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    assert (dest / "appsec").is_dir()
    assert not (dest / _TEMPLATE_PKG).exists()


def test_transform_replaces_underscore_form_in_init(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    init = (dest / "appsec" / "__init__.py").read_text()
    assert _TEMPLATE_PKG not in init
    assert "appsec" in init


def test_transform_replaces_hyphen_form_in_pyproject(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    assert _TEMPLATE_REPO not in pyproject
    assert "appsec" in pyproject


def test_transform_replaces_underscore_form_in_pyproject(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    assert _TEMPLATE_PKG not in pyproject


def test_transform_sets_description_in_pyproject(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec security scanner.", "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'description = "AppSec security scanner."' in pyproject
    assert "clonable" not in pyproject


def test_transform_replaces_culture_yaml_suffix(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    text = (dest / "culture.yaml").read_text()
    assert _TEMPLATE_REPO not in text
    assert "appsec" in text


def test_transform_replaces_sonar_keys(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    text = (dest / "sonar-project.properties").read_text()
    assert _TEMPLATE_REPO not in text
    assert _TEMPLATE_PKG not in text
    assert "appsec" in text


def test_transform_replaces_in_skill_md(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    text = (dest / ".claude" / "skills" / "cicd" / "SKILL.md").read_text()
    assert _TEMPLATE_REPO not in text
    assert "appsec" in text


def test_transform_replaces_in_skills_local_yaml_example(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    text = (dest / ".claude" / "skills.local.yaml.example").read_text()
    assert _TEMPLATE_REPO not in text
    assert "appsec" in text


def test_transform_skips_git_dir(tmp_path):
    dest = _build_fixture(tmp_path)
    original_git_config = (dest / ".git" / "config").read_text()
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    # .git/config must be untouched (no substitution inside .git/).
    assert (dest / ".git" / "config").read_text() == original_git_config


def test_transform_writes_claude_md_seed_for_claude_backend(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec scanner.", "claude")
    seed = (dest / "CLAUDE.md").read_text()
    # Must name the agent.
    assert "appsec" in seed
    # Must embed the description.
    assert "AppSec scanner." in seed
    # Must carry a /init instruction.
    assert "/init" in seed
    # Must NOT keep the template's "clonable template" prose.
    assert "clonable" not in seed
    # Must be valid for steward doctor — CLAUDE.md present, identifies backend.
    assert "backend: claude" in seed or "backend-consistency" in seed or "CLAUDE.md" in seed


def test_transform_writes_agents_md_seed_for_acp_backend(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec scanner.", "acp")
    seed = (dest / "AGENTS.md").read_text()
    assert "appsec" in seed
    assert "AppSec scanner." in seed
    assert "/init" in seed
    # For acp backend, CLAUDE.md should NOT be written (or its content replaced).
    # The seed file is AGENTS.md for acp.
    assert "AGENTS.md" in seed


def test_transform_readme_heading_updated(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec security scanner.", "claude")
    readme = (dest / "README.md").read_text()
    # First heading must name the new agent.
    first_heading = re.search(r"^#\s+(.+)$", readme, re.MULTILINE)
    assert first_heading is not None
    assert "appsec" in first_heading.group(1).lower()


def test_transform_readme_embeds_desc(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec security scanner.", "claude")
    readme = (dest / "README.md").read_text()
    assert "AppSec security scanner." in readme


def test_transform_hyphenated_name(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "my-agent", "A hyphenated agent.", "claude")
    # package dir uses underscore form
    assert (dest / "my_agent").is_dir()
    # pyproject uses hyphen form for name
    pyproject = (dest / "pyproject.toml").read_text()
    assert "my-agent" in pyproject
    assert "my_agent" in pyproject
    assert _TEMPLATE_PKG not in pyproject
    assert _TEMPLATE_REPO not in pyproject


def test_transform_invalid_backend_raises(tmp_path):
    dest = _build_fixture(tmp_path)
    with pytest.raises(ValueError, match="backend"):
        transform_clone(dest, "appsec", "desc", "invalid")


def test_transform_missing_dest_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        transform_clone(tmp_path / "nonexistent", "appsec", "desc", "claude")
