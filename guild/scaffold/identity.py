"""Identity-file generator for new AgentCulture siblings.

Provides ``build()``, a pure function that returns the contents of the three
identity files a new sibling needs:

- The prompt file (``CLAUDE.md`` for ``backend="claude"``,
  ``AGENTS.md`` for ``backend="acp"``) — a *self-initializing seed*, not a
  finished runtime prompt.  It names the agent, embeds the description, and
  carries an explicit ``/init``-style re-init instruction so the new agent
  expands the seed into its full runtime prompt once it lands.
- ``culture.yaml`` — declares the agent suffix + backend so that
  ``steward doctor`` backend-consistency and prompt-file-present invariants
  are satisfied immediately.
- ``.claude/skills.local.yaml.example`` — portable per-machine config
  template (workspace-relative paths only, no hardcoded home dirs).

The function is PURE: no file writes, no subprocess, no network.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Backend → prompt-file mapping
# ---------------------------------------------------------------------------

_PROMPT_FILES: dict[str, str] = {
    "claude": "CLAUDE.md",
    "acp": "AGENTS.md",
}


def _bare_name(agent: str) -> str:
    """Return the bare repo name from an 'org/repo' or plain 'name' string."""
    return agent.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# Individual file renderers
# ---------------------------------------------------------------------------


def _render_prompt_file(agent: str, desc: str, backend: str) -> str:
    """Render the CLAUDE.md (or AGENTS.md) seed for a new sibling.

    This is intentionally minimal — a *seed* the new agent will expand via
    ``/init``.  It must:
      - identify itself as a seed/placeholder,
      - name the agent and embed the description,
      - carry an explicit, actionable re-init instruction.
    """
    bare = _bare_name(agent)
    prompt_file = _PROMPT_FILES[backend]

    return f"""\
# {prompt_file} — seed / bootstrap placeholder

> **This is a self-initializing seed, not a finished runtime prompt.**
> Run `/init` (or describe the agent's domain to your AI assistant) to
> re-initialize this file into a full runtime prompt, using the description
> below and the scaffolded repo as context.

## Agent

**{bare}**

## Description

{desc.rstrip()}

## Re-init instruction

This file is a seed. To expand it into your full runtime prompt:

1. Open this repo in Claude Code (or your preferred AI assistant).
2. Run `/init` — the assistant will read the repo, incorporate the description
   above, and replace this seed with a complete `{prompt_file}`.
3. Commit the result.

Until you run `/init`, `{bare}` satisfies the `steward doctor`
`prompt-file-present` and `backend-consistency` invariants (a `{prompt_file}`
exists and `culture.yaml` declares `backend: {backend}`) but the prompt is not
yet tailored to this agent's domain.
"""


def _render_culture_yaml(agent: str, backend: str) -> str:
    """Render a minimal culture.yaml for the new sibling."""
    bare = _bare_name(agent)
    return f"""\
agents:
- suffix: {bare}
  backend: {backend}
"""


def _render_skills_local_yaml_example(agent: str) -> str:
    """Render a portable skills.local.yaml.example for the new sibling.

    Uses workspace-relative paths (``../foo``) so no absolute home dirs are
    embedded.  The caller (or the new agent) fills in real sibling paths.
    """
    bare = _bare_name(agent)
    return f"""\
# Per-machine config for {bare}'s skills.
# Copy this file to .claude/skills.local.yaml (git-ignored) and adjust for
# your environment.  Skills read skills.local.yaml first, falling back to
# this example.

# Path to the Culture server's agent manifest (suffix -> directory mapping).
# Used by skills that resolve a registered agent suffix to its repo directory
# — e.g. the agent-config skill.
# Set this to the absolute path of your Culture server.yaml on each machine.
# Example (fill in your actual path): culture_server_yaml: /path/to/.culture/server.yaml
# culture_server_yaml:

# Workspace root — the parent directory that holds sibling repos side-by-side.
# If unset, skills default to this repo's parent directory.
# workspace_root: ..

# Sibling project paths checked by cross-repo skills (cicd alignment delta,
# communicate).  Workspace-relative paths (../foo) are preferred.  Skills skip
# entries that don't exist on disk, so commenting out missing ones is fine.
sibling_projects:
  - ../guildmaster
  - ../steward
  - ../culture
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build(
    agent: str,
    desc: str,
    backend: str = "claude",
) -> dict[str, str]:
    """Generate the identity files for a new AgentCulture sibling.

    Returns a ``dict[relpath, content]`` covering:
    - The prompt file (``CLAUDE.md`` or ``AGENTS.md``, depending on
      ``backend``) — a self-initializing seed carrying a ``/init`` re-init
      instruction.
    - ``culture.yaml`` — declares the agent's ``suffix`` and ``backend``.
    - ``.claude/skills.local.yaml.example`` — portable per-machine config.

    This function is PURE: no file writes, no subprocess, no network.

    Args:
        agent: The agent name, either a bare name (``"mybot"``) or an
               ``"org/repo"`` slug.  The bare repo name is used as the
               ``suffix`` in ``culture.yaml``.
        desc:  A short description of the agent's purpose, embedded in the
               prompt-file seed.
        backend: ``"claude"`` (default) or ``"acp"``.  Controls which prompt
                 file is generated (``CLAUDE.md`` / ``AGENTS.md``) and the
                 ``backend`` value in ``culture.yaml``.

    Returns:
        ``dict[str, str]`` — keys are repo-relative file paths, values are
        file contents (strings, never bytes).

    Raises:
        ValueError: If ``backend`` is not ``"claude"`` or ``"acp"``.
    """
    if backend not in _PROMPT_FILES:
        raise ValueError(f"backend must be one of {sorted(_PROMPT_FILES)!r}, got {backend!r}")

    prompt_file = _PROMPT_FILES[backend]

    return {
        prompt_file: _render_prompt_file(agent, desc, backend),
        "culture.yaml": _render_culture_yaml(agent, backend),
        ".claude/skills.local.yaml.example": _render_skills_local_yaml_example(agent),
    }
