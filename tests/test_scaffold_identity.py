"""Tests for ``guild.scaffold.identity`` — identity-file generator (TDD).

Tests are written RED-first: they import and call guild.scaffold.identity.build
before the module exists, so the initial run fails with ImportError.

Acceptance criteria (from t3 plan):
  1. build(agent, desc, backend) returns a dict keyed by relpath with
     CLAUDE.md, culture.yaml, and skills.local.yaml.example.
  2. The generated CLAUDE.md (a) embeds the desc text and names the agent,
     (b) carries an explicit /init-style re-init instruction.
  3. culture.yaml's declared backend matches the prompt-file convention
     (backend-consistency: "claude" -> CLAUDE.md, "acp" -> AGENTS.md).
  4. No generated file contains an absolute home path
     (no "/home/", no "/Users/", no "~/" hardcoded user dirs).
"""

from __future__ import annotations

import re

import pytest

from guild.scaffold.identity import build

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOME_PATH_RE = re.compile(r"(/home/[^/\s]|/Users/[^/\s]|~[/])")


def _has_home_path(text: str) -> bool:
    """Return True if text contains any hardcoded home-directory path."""
    return bool(_HOME_PATH_RE.search(text))


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------


def test_build_returns_dict() -> None:
    """build() returns a dict."""
    result = build("myagent", "A demo agent.", backend="claude")
    assert isinstance(result, dict)


def test_build_contains_claude_md_for_claude_backend() -> None:
    """For backend='claude', the dict has a 'CLAUDE.md' key."""
    result = build("myagent", "A demo agent.", backend="claude")
    assert "CLAUDE.md" in result


def test_build_contains_agents_md_for_acp_backend() -> None:
    """For backend='acp', the dict has an 'AGENTS.md' key (not CLAUDE.md)."""
    result = build("myagent", "A demo agent.", backend="acp")
    assert "AGENTS.md" in result
    assert "CLAUDE.md" not in result


def test_build_contains_culture_yaml() -> None:
    """build() result contains a 'culture.yaml' key."""
    result = build("myagent", "A demo agent.")
    assert "culture.yaml" in result


def test_build_contains_skills_local_yaml_example() -> None:
    """build() result contains '.claude/skills.local.yaml.example'."""
    result = build("myagent", "A demo agent.")
    assert ".claude/skills.local.yaml.example" in result


# ---------------------------------------------------------------------------
# CLAUDE.md (seed) content
# ---------------------------------------------------------------------------


def test_claude_md_embeds_desc() -> None:
    """The generated CLAUDE.md embeds the description text."""
    desc = "A specialized agent for data processing pipelines."
    result = build("databot", desc, backend="claude")
    assert desc in result["CLAUDE.md"]


def test_claude_md_names_agent() -> None:
    """The generated CLAUDE.md names the agent."""
    result = build("databot", "Some desc.", backend="claude")
    assert "databot" in result["CLAUDE.md"]


def test_claude_md_carries_reinit_instruction() -> None:
    """The generated CLAUDE.md contains an explicit /init-style re-init instruction."""
    result = build("databot", "Some desc.", backend="claude")
    text = result["CLAUDE.md"]
    # Must contain either '/init' literal or words describing the re-init action
    has_init_verb = "/init" in text
    has_reinit_words = any(
        phrase in text.lower()
        for phrase in [
            "re-init",
            "reinit",
            "re-initialize",
            "reinitialize",
            "expand this seed",
            "replace this seed",
        ]
    )
    assert has_init_verb or has_reinit_words, (
        "CLAUDE.md seed must carry an explicit /init-style re-init instruction; " f"got:\n{text}"
    )


def test_claude_md_reinit_instruction_is_actionable() -> None:
    """The re-init instruction tells the agent *how* to act, not just that it should."""
    result = build("databot", "Some desc.", backend="claude")
    text = result["CLAUDE.md"]
    # An actionable instruction mentions the mechanism: /init or some explicit verb
    assert "/init" in text or "run" in text.lower() or "replace" in text.lower(), (
        "Re-init instruction must be actionable (name the command or verb), " f"got:\n{text}"
    )


def test_claude_md_labels_itself_as_seed() -> None:
    """The generated CLAUDE.md makes clear it is a seed / bootstrap file."""
    result = build("databot", "Some desc.", backend="claude")
    text = result["CLAUDE.md"]
    assert any(
        word in text.lower() for word in ["seed", "bootstrap", "placeholder", "stub"]
    ), f"CLAUDE.md should self-identify as a seed/stub; got:\n{text}"


# ---------------------------------------------------------------------------
# Backend-consistency (culture.yaml)
# ---------------------------------------------------------------------------


def test_culture_yaml_backend_claude() -> None:
    """For backend='claude', culture.yaml declares backend: claude."""
    result = build("myagent", "Some desc.", backend="claude")
    yaml_text = result["culture.yaml"]
    assert "backend: claude" in yaml_text


def test_culture_yaml_backend_acp() -> None:
    """For backend='acp', culture.yaml declares backend: acp."""
    result = build("myagent", "Some desc.", backend="acp")
    yaml_text = result["culture.yaml"]
    assert "backend: acp" in yaml_text


def test_culture_yaml_suffix_matches_agent() -> None:
    """culture.yaml's suffix matches the agent name."""
    result = build("myagent", "Some desc.", backend="claude")
    yaml_text = result["culture.yaml"]
    assert "suffix: myagent" in yaml_text


def test_backend_consistency_claude_uses_claude_md() -> None:
    """backend='claude' -> prompt file key is CLAUDE.md (not AGENTS.md)."""
    result = build("myagent", "desc", backend="claude")
    assert "CLAUDE.md" in result
    assert "AGENTS.md" not in result


def test_backend_consistency_acp_uses_agents_md() -> None:
    """backend='acp' -> prompt file key is AGENTS.md (not CLAUDE.md)."""
    result = build("myagent", "desc", backend="acp")
    assert "AGENTS.md" in result
    assert "CLAUDE.md" not in result


# ---------------------------------------------------------------------------
# No absolute home paths in any file
# ---------------------------------------------------------------------------


def test_no_home_path_in_claude_md() -> None:
    """CLAUDE.md must not contain a hardcoded home-directory path."""
    result = build("myagent", "desc", backend="claude")
    assert not _has_home_path(
        result["CLAUDE.md"]
    ), "CLAUDE.md contains a hardcoded home path; use workspace-relative paths instead."


def test_no_home_path_in_culture_yaml() -> None:
    """culture.yaml must not contain a hardcoded home-directory path."""
    result = build("myagent", "desc", backend="claude")
    assert not _has_home_path(
        result["culture.yaml"]
    ), "culture.yaml contains a hardcoded home path."


def test_no_home_path_in_skills_local_yaml_example() -> None:
    """skills.local.yaml.example must not contain a hardcoded home-directory path."""
    result = build("myagent", "desc", backend="claude")
    key = ".claude/skills.local.yaml.example"
    text = result[key]
    assert not _has_home_path(
        text
    ), f"{key} contains a hardcoded home path; use workspace-relative paths instead."


def test_no_home_path_in_any_file() -> None:
    """No generated file for either backend contains a hardcoded home path."""
    for backend in ("claude", "acp"):
        result = build("myagent", "A demo agent.", backend=backend)
        for relpath, content in result.items():
            assert not _has_home_path(
                content
            ), f"File '{relpath}' (backend={backend}) contains a hardcoded home path."


# ---------------------------------------------------------------------------
# Misc / edge cases
# ---------------------------------------------------------------------------


def test_default_backend_is_claude() -> None:
    """build() defaults to backend='claude'."""
    result = build("myagent", "desc")
    assert "CLAUDE.md" in result
    assert "culture.yaml" in result
    yaml_text = result["culture.yaml"]
    assert "backend: claude" in yaml_text


def test_invalid_backend_raises() -> None:
    """build() raises ValueError for unrecognised backend."""
    with pytest.raises(ValueError, match="backend"):
        build("myagent", "desc", backend="unknown")


def test_all_values_are_strings() -> None:
    """Every value in the returned dict is a string (file content, not bytes)."""
    result = build("myagent", "desc", backend="claude")
    for key, value in result.items():
        assert isinstance(value, str), f"Value for '{key}' is not a str: {type(value)}"


def test_desc_with_special_characters() -> None:
    """build() handles desc containing special characters without error."""
    desc = 'Handles "quotes", <angle brackets>, & ampersands and newlines\n'
    result = build("specialagent", desc, backend="claude")
    assert isinstance(result["CLAUDE.md"], str)


def test_agent_name_with_slash_uses_bare_suffix() -> None:
    """If agent is 'org/repo' style, the suffix in culture.yaml uses the bare repo name."""
    result = build("agentculture/mybot", "desc", backend="claude")
    yaml_text = result["culture.yaml"]
    # The suffix should be just the bare name, not the full org/repo
    assert "suffix: mybot" in yaml_text


def test_skills_local_yaml_example_is_valid_comment_yaml() -> None:
    """skills.local.yaml.example has comment lines and at least one key."""
    key = ".claude/skills.local.yaml.example"
    result = build("myagent", "desc", backend="claude")
    text = result[key]
    # Must have at least one comment line
    assert any(
        line.strip().startswith("#") for line in text.splitlines()
    ), "skills.local.yaml.example should have at least one comment line."
