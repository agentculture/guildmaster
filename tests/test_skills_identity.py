"""Tests for ``guild.skills.identity`` — onboarding identity-setup section renderer."""

from __future__ import annotations

from guild.skills.identity import identity_section


def test_identity_section_returns_markdown_string() -> None:
    """identity_section returns a string."""
    result = identity_section()
    assert isinstance(result, str)


def test_identity_section_mentions_culture_yaml() -> None:
    """The section mentions culture.yaml, the core identity file."""
    result = identity_section()
    assert "culture.yaml" in result


def test_identity_section_mentions_backend() -> None:
    """The section mentions the backend parameter."""
    result = identity_section(backend="claude")
    assert "backend" in result.lower()


def test_identity_section_mentions_suffix() -> None:
    """The section mentions suffix (agent identity in culture.yaml)."""
    result = identity_section()
    assert "suffix" in result


def test_identity_section_mentions_claude_md_for_claude_backend() -> None:
    """For backend='claude', the section names CLAUDE.md as the prompt file."""
    result = identity_section(backend="claude")
    assert "CLAUDE.md" in result


def test_identity_section_mentions_agents_md_for_acp_backend() -> None:
    """For backend='acp', the section names AGENTS.md as the prompt file."""
    result = identity_section(backend="acp")
    assert "AGENTS.md" in result


def test_identity_section_with_agent_references_agent_name() -> None:
    """When agent is provided, the section references it by name."""
    result = identity_section(agent="mysilo")
    assert "mysilo" in result


def test_identity_section_without_agent_uses_generic_language() -> None:
    """When agent is None, the section uses generic language like 'your' or 'the agent'."""
    result = identity_section(agent=None)
    # Should use generic terms when no specific agent is given
    assert any(term in result.lower() for term in ["agent", "sibling", "repo"])


def test_identity_section_backend_to_prompt_mapping_claude() -> None:
    """For backend='claude', the section establishes the CLAUDE.md association."""
    result = identity_section(backend="claude")
    # Should mention both claude and CLAUDE.md to establish the mapping
    assert "claude" in result.lower()
    assert "CLAUDE.md" in result


def test_identity_section_backend_to_prompt_mapping_acp() -> None:
    """For backend='acp', the section establishes the AGENTS.md association."""
    result = identity_section(backend="acp")
    # Should mention both acp and AGENTS.md to establish the mapping
    assert "acp" in result.lower()
    assert "AGENTS.md" in result


def test_identity_section_is_checklist_like() -> None:
    """The section reads like a checklist that a human/agent can follow."""
    result = identity_section(agent="example-agent")
    # Should have some structure to make it followable
    # Check for typical checklist markers or clear steps
    lines = result.strip().split("\n")
    assert len(lines) > 1, "section should have multiple lines to be followable"


def test_identity_section_covers_prompt_file_present_invariant() -> None:
    """The section guides toward satisfying prompt-file-present (repo has the prompt file)."""
    result_claude = identity_section(backend="claude")
    result_acp = identity_section(backend="acp")

    # Both should mention needing to create/have the prompt file
    assert "CLAUDE.md" in result_claude
    assert "AGENTS.md" in result_acp


def test_identity_section_covers_backend_consistency_invariant() -> None:
    """The section guides toward satisfying backend-consistency (backend and prompt agree)."""
    result = identity_section(agent="test-agent", backend="claude")

    # Should establish that backend and prompt file go together
    assert "claude" in result.lower()
    assert "CLAUDE.md" in result
    # The section should make the connection between them clear
    assert result.count("claude") > 0  # References backend


def test_identity_section_with_all_parameters() -> None:
    """identity_section works with both agent and backend specified."""
    result = identity_section(agent="my-agent", backend="acp")
    assert "my-agent" in result
    assert "acp" in result.lower()
    assert "AGENTS.md" in result
