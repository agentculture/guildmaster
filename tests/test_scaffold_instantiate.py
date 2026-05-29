"""Tests for guild.scaffold.instantiate — the pure template transform (t-inst).

These tests work entirely against a fixture directory built in tmp_path; no
network, no subprocess, no real github.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guild.scaffold.instantiate import (
    _resolve_identifiers,
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

    # Package directory with __init__.py that imports from the package and reads
    # its version from the *distribution* metadata (hyphen form, like the real
    # template's `importlib.metadata` lookup).
    pkg_dir = tmp_path / _TEMPLATE_PKG
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        '"""culture_agent_template package."""\n'
        "from importlib.metadata import version as _pkg_version\n"
        "from culture_agent_template import cli  # noqa: F401\n"
        '\n__version__ = _pkg_version("culture-agent-template")\n'
    )

    # .github/workflows/publish.yml — the TestPyPI install hint pins the dist.
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "publish.yml").write_text(
        "name: publish\n"
        "jobs:\n"
        "  test-publish:\n"
        "    steps:\n"
        '      - run: echo "install culture-agent-template==${DEV_VERSION}"\n'
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


def test_transform_escapes_description_for_toml(tmp_path):
    """A desc with quotes/backslashes must yield valid, round-tripping TOML."""
    import tomllib

    dest = _build_fixture(tmp_path)
    tricky = 'Scans for "secrets" and C:\\paths\\here'
    transform_clone(dest, "appsec", tricky, "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    data = tomllib.loads(pyproject)  # must parse without error
    assert data["project"]["description"] == tricky


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
    # First "# " heading must name the new agent (plain string scan — avoids a
    # backtracking-prone regex / Sonar DoS hotspot).
    heading = next((ln for ln in readme.splitlines() if ln.startswith("# ")), None)
    assert heading is not None
    assert "appsec" in heading.lower()


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


def test_transform_readme_replaces_multiline_intro_paragraph(tmp_path):
    """A *multi-line* template intro must be replaced wholesale — the real
    culture-agent-template intro spans several lines, and replacing only the
    first leaves a dangling fragment (regression: agenda genesis README)."""
    dest = _build_fixture(tmp_path)
    (dest / "README.md").write_text(
        "# culture-agent-template\n\n"
        "A clonable AgentCulture agent template with a consistent structure,\n"
        "lifecycle, and skills. Clone it, rename the package, and edit\n"
        "`culture.yaml` to make it your own.\n\n"
        "## More\n\nMore docs.\n"
    )
    transform_clone(dest, "appsec", "AppSec security scanner.", "claude")
    readme = (dest / "README.md").read_text()
    # New description present; the entire old intro paragraph is gone.
    assert "AppSec security scanner." in readme
    assert "lifecycle, and skills" not in readme
    assert "Clone it, rename the package" not in readme
    assert "make it your own" not in readme
    # Body after the intro paragraph is preserved.
    assert "## More" in readme
    assert "More docs." in readme


def test_transform_readme_stops_intro_at_block_without_blank_line(tmp_path):
    """Intro-paragraph consumption must stop at the start of a new markdown
    block even when no blank line separates it from the intro stub — otherwise
    a following heading/list/badge is silently dropped (Qodo, PR #29)."""
    dest = _build_fixture(tmp_path)
    (dest / "README.md").write_text(
        "# culture-agent-template\n\n"
        "A clonable template.\n"  # stub immediately followed by a heading
        "## Features\n\n- one\n- two\n"
    )
    transform_clone(dest, "appsec", "AppSec scanner.", "claude")
    readme = (dest / "README.md").read_text()
    assert "AppSec scanner." in readme
    assert "A clonable template." not in readme  # stub replaced
    # The block that immediately follows the stub must survive.
    assert "## Features" in readme
    assert "- one" in readme
    assert "- two" in readme


def test_transform_readme_consumes_wrapped_inline_code_prose(tmp_path):
    """A continuation line beginning with a *single* backtick (inline code) is
    wrapped prose, not a block start, so it is consumed with the intro."""
    dest = _build_fixture(tmp_path)
    (dest / "README.md").write_text(
        "# culture-agent-template\n\n"
        "A clonable template you configure by editing\n"
        "`culture.yaml` to taste.\n\n"
        "## More\n"
    )
    transform_clone(dest, "appsec", "AppSec scanner.", "claude")
    readme = (dest / "README.md").read_text()
    assert "AppSec scanner." in readme
    assert "culture.yaml` to taste" not in readme  # backtick prose consumed
    assert "## More" in readme


# ---------------------------------------------------------------------------
# --dist retarget tests
# ---------------------------------------------------------------------------


def test_transform_default_dist_leaves_repo_token(tmp_path):
    """No dist → the dist name stays the global-replace result (repo_token)."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "appsec"' in pyproject
    init = (dest / "appsec" / "__init__.py").read_text()
    assert '_pkg_version("appsec")' in init


def test_transform_dist_equal_repo_token_is_noop(tmp_path):
    """Explicitly passing dist == repo_token changes nothing (no-op guard)."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="appsec")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "appsec"' in pyproject
    assert "appsec-cli" not in pyproject


def test_transform_custom_dist_retargets_pyproject_name(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="appsec-cli")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "appsec-cli"' in pyproject


def test_transform_custom_dist_retargets_init_metadata(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="appsec-cli")
    init = (dest / "appsec" / "__init__.py").read_text()
    assert '_pkg_version("appsec-cli")' in init


def test_transform_custom_dist_retargets_publish_pin(tmp_path):
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="appsec-cli")
    wf = (dest / ".github" / "workflows" / "publish.yml").read_text()
    assert "appsec-cli==${DEV_VERSION}" in wf
    assert "appsec==${DEV_VERSION}" not in wf


def test_transform_custom_dist_keeps_command_and_package(tmp_path):
    """The dist rename must NOT touch the console command or the package dir."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="appsec-cli")
    # Package dir stays the import name.
    assert (dest / "appsec").is_dir()
    pyproject = (dest / "pyproject.toml").read_text()
    # The console script (under [project.scripts]) stays the bare command.
    assert 'appsec = "appsec.cli:main"' in pyproject
    # packages list stays the import name.
    assert 'packages = ["appsec"]' in pyproject


def test_transform_custom_dist_hyphenated_repo(tmp_path):
    """A hyphenated repo (my-agent) with a custom dist still retargets correctly."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "my-agent", "Hyphenated.", "claude", dist="my-agent-cli")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "my-agent-cli"' in pyproject
    # command + package (underscore) untouched.
    assert (dest / "my_agent").is_dir()
    assert 'my-agent = "my_agent.cli:main"' in pyproject


def test_transform_plan_includes_dist_default(tmp_path):
    plan = transform_plan("appsec", "AppSec agent.")
    assert plan["dist"] == "appsec"
    # No retarget step when dist == repo_token.
    assert not any("retarget" in s.lower() for s in plan["steps"])


def test_transform_plan_includes_dist_custom(tmp_path):
    plan = transform_plan("appsec", "AppSec agent.", dist="appsec-cli")
    assert plan["dist"] == "appsec-cli"
    assert any("retarget" in s.lower() and "appsec-cli" in s for s in plan["steps"])


def test_transform_clone_empty_dist_raises(tmp_path):
    """An explicitly-empty dist is a programming error, not "use the default"."""
    dest = _build_fixture(tmp_path)
    with pytest.raises(ValueError, match="dist"):
        transform_clone(dest, "appsec", "AppSec agent.", "claude", dist="")


def test_transform_plan_whitespace_dist_raises():
    with pytest.raises(ValueError, match="dist"):
        transform_plan("appsec", "AppSec agent.", dist="   ")


# ---------------------------------------------------------------------------
# _resolve_identifiers — the shared resolver
# ---------------------------------------------------------------------------


def test_resolve_identifiers_defaults():
    """No overrides → legacy behaviour (pkg = underscore of repo; all = repo)."""
    eff_pkg, repo_token, eff_command, eff_dist = _resolve_identifiers("my-agent")
    assert (eff_pkg, repo_token, eff_command, eff_dist) == (
        "my_agent",
        "my-agent",
        "my-agent",
        "my-agent",
    )


def test_resolve_identifiers_command_only_pkg_follows_command():
    """--command alone also moves the import package (underscore of command)."""
    eff_pkg, repo_token, eff_command, eff_dist = _resolve_identifiers(
        "reachy-mini-cli", command="reachy"
    )
    assert eff_command == "reachy"
    assert eff_pkg == "reachy"  # underscore form of the command, NOT the repo
    assert repo_token == "reachy-mini-cli"
    assert eff_dist == "reachy-mini-cli"


def test_resolve_identifiers_pkg_decouples_from_command():
    """--pkg overrides the package without touching the command."""
    eff_pkg, repo_token, eff_command, eff_dist = _resolve_identifiers(
        "reachy-mini-cli", pkg="myimport", command="reachy"
    )
    assert eff_command == "reachy"
    assert eff_pkg == "myimport"


def test_resolve_identifiers_full_split():
    eff_pkg, repo_token, eff_command, eff_dist = _resolve_identifiers(
        "reachy-mini-cli", command="reachy", dist="reachy-cli"
    )
    assert (eff_pkg, repo_token, eff_command, eff_dist) == (
        "reachy",
        "reachy-mini-cli",
        "reachy",
        "reachy-cli",
    )


def test_resolve_identifiers_empty_command_raises():
    with pytest.raises(ValueError, match="command"):
        _resolve_identifiers("appsec", command="")


def test_resolve_identifiers_empty_pkg_raises():
    with pytest.raises(ValueError, match="pkg"):
        _resolve_identifiers("appsec", pkg="  ")


# ---------------------------------------------------------------------------
# rename_map with a custom pkg
# ---------------------------------------------------------------------------


def test_rename_map_custom_pkg():
    m = rename_map("reachy-mini-cli", pkg="reachy")
    assert m["culture_agent_template"] == "reachy"
    assert m["culture-agent-template"] == "reachy-mini-cli"


# ---------------------------------------------------------------------------
# transform_plan — command / pkg
# ---------------------------------------------------------------------------


def test_transform_plan_command_default_no_retarget_step():
    plan = transform_plan("appsec", "AppSec agent.")
    assert plan["command"] == "appsec"
    assert not any("retarget console command" in s for s in plan["steps"])


def test_transform_plan_command_custom_adds_step():
    plan = transform_plan("reachy-mini-cli", "Robot agent.", command="reachy")
    assert plan["command"] == "reachy"
    assert plan["pkg"] == "reachy"
    assert any("retarget console command" in s and "reachy" in s for s in plan["steps"])


def test_transform_plan_pkg_custom_reflected():
    plan = transform_plan("reachy-mini-cli", "Robot agent.", command="reachy", pkg="myimport")
    assert plan["pkg"] == "myimport"
    # The global-replace + dir-rename steps name the custom package.
    assert any("myimport" in s for s in plan["steps"])


def test_transform_plan_full_split():
    plan = transform_plan("reachy-mini-cli", "Robot agent.", command="reachy", dist="reachy-cli")
    assert plan["repo_token"] == "reachy-mini-cli"
    assert plan["command"] == "reachy"
    assert plan["pkg"] == "reachy"
    assert plan["dist"] == "reachy-cli"
    assert any("retarget console command" in s for s in plan["steps"])
    assert any("retarget PyPI distribution" in s for s in plan["steps"])


# ---------------------------------------------------------------------------
# transform_clone — command / pkg retargets
# ---------------------------------------------------------------------------


def test_transform_command_only_retargets_scripts_key(tmp_path):
    """--command rewrites only the [project.scripts] key; pkg follows command."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "reachy-mini-cli", "Robot agent.", "claude", command="reachy")
    pyproject = (dest / "pyproject.toml").read_text()
    # Command key is the custom command; module path uses the package (= command).
    assert 'reachy = "reachy.cli:main"' in pyproject
    # [project].name stays the repo identity (no --dist).
    assert 'name = "reachy-mini-cli"' in pyproject
    # Package dir + packages list follow the command (underscore form).
    assert (dest / "reachy").is_dir()
    assert 'packages = ["reachy"]' in pyproject


def test_transform_command_retargets_indented_scripts_key(tmp_path):
    """An indented [project.scripts] entry (valid TOML) is still retargeted."""
    dest = _build_fixture(tmp_path)
    # Re-write pyproject with an INDENTED scripts key (valid TOML formatting).
    (dest / "pyproject.toml").write_text(
        '[project]\nname = "culture-agent-template"\n'
        'description = "x"\n'
        'packages = ["culture_agent_template"]\n'
        "\n[project.scripts]\n"
        '    culture-agent-template = "culture_agent_template.cli:main"\n'
    )
    transform_clone(dest, "reachy-mini-cli", "Robot.", "claude", command="reachy")
    pyproject = (dest / "pyproject.toml").read_text()
    # The key was rewritten AND its indentation preserved.
    assert '    reachy = "reachy.cli:main"' in pyproject
    assert "reachy-mini-cli =" not in pyproject
    # [project].name (the dist) is untouched — no --dist.
    assert 'name = "reachy-mini-cli"' in pyproject


def test_transform_command_only_keeps_repo_identity(tmp_path):
    """README heading, culture.yaml suffix, and the seed stay the repo token."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "reachy-mini-cli", "Robot agent.", "claude", command="reachy")
    assert "# reachy-mini-cli" in (dest / "README.md").read_text()
    assert "suffix: reachy-mini-cli" in (dest / "culture.yaml").read_text()
    claude_md = (dest / "CLAUDE.md").read_text()
    assert "reachy-mini-cli" in claude_md


def test_transform_pkg_only_renames_package_not_command(tmp_path):
    """--pkg moves the import package; the command + dist stay the repo token."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec agent.", "claude", pkg="appsec_core")
    assert (dest / "appsec_core").is_dir()
    assert not (dest / "appsec").exists()
    pyproject = (dest / "pyproject.toml").read_text()
    # Command key stays the repo token; module path uses the custom package.
    assert 'appsec = "appsec_core.cli:main"' in pyproject
    assert 'packages = ["appsec_core"]' in pyproject
    assert 'name = "appsec"' in pyproject  # dist unchanged
    init = (dest / "appsec_core" / "__init__.py").read_text()
    assert "from appsec_core import cli" in init


def test_transform_full_split_reachy(tmp_path):
    """The first intended use: repo reachy-mini-cli / command+pkg reachy / dist reachy-cli."""
    dest = _build_fixture(tmp_path)
    transform_clone(
        dest,
        "reachy-mini-cli",
        "Robot agent.",
        "claude",
        command="reachy",
        dist="reachy-cli",
    )
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "reachy-cli"' in pyproject  # dist
    assert 'reachy = "reachy.cli:main"' in pyproject  # command key + pkg value
    assert 'packages = ["reachy"]' in pyproject  # import package
    assert (dest / "reachy").is_dir()
    init = (dest / "reachy" / "__init__.py").read_text()
    assert '_pkg_version("reachy-cli")' in init  # metadata lookup = dist
    wf = (dest / ".github" / "workflows" / "publish.yml").read_text()
    assert "reachy-cli==${DEV_VERSION}" in wf  # publish pin = dist
    # Identity stays the repo token.
    assert "# reachy-mini-cli" in (dest / "README.md").read_text()
    assert "suffix: reachy-mini-cli" in (dest / "culture.yaml").read_text()


def test_transform_no_overrides_byte_identical_to_legacy(tmp_path):
    """No command/pkg/dist overrides → the legacy single-token result."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "my-agent", "Hyphenated.", "claude")
    pyproject = (dest / "pyproject.toml").read_text()
    assert 'name = "my-agent"' in pyproject
    assert 'my-agent = "my_agent.cli:main"' in pyproject
    assert 'packages = ["my_agent"]' in pyproject
    assert (dest / "my_agent").is_dir()


def test_transform_clone_empty_command_raises(tmp_path):
    dest = _build_fixture(tmp_path)
    with pytest.raises(ValueError, match="command"):
        transform_clone(dest, "appsec", "AppSec agent.", "claude", command="")


def test_transform_clone_empty_pkg_raises(tmp_path):
    dest = _build_fixture(tmp_path)
    with pytest.raises(ValueError, match="pkg"):
        transform_clone(dest, "appsec", "AppSec agent.", "claude", pkg="   ")


def test_transform_seed_avoids_md036_standalone_emphasis(tmp_path):
    """The CLAUDE.md seed must not place the agent name on a standalone
    emphasized line (markdownlint MD036 no-emphasis-as-heading — this broke
    the agenda genesis CI lint job)."""
    dest = _build_fixture(tmp_path)
    transform_clone(dest, "appsec", "AppSec scanner.", "claude")
    seed_lines = [ln.strip() for ln in (dest / "CLAUDE.md").read_text().splitlines()]
    assert "**appsec**" not in seed_lines
    # The name still appears, inlined in prose.
    assert any("appsec" in ln for ln in seed_lines)
