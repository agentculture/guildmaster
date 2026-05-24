"""Onboarding identity-setup section renderer for new AgentCulture siblings.

Provides a function to generate a Markdown section that walks a new sibling
through establishing its identity (culture.yaml + prompt file) to satisfy
steward doctor invariants: prompt-file-present and backend-consistency.
"""

from __future__ import annotations


def identity_section(agent: str | None = None, backend: str = "claude") -> str:
    """Render the onboarding identity-setup section.

    Returns a Markdown section that walks a new sibling through establishing
    its identity so it would satisfy prompt-file-present + backend-consistency.

    Args:
        agent: Optional agent name (suffix). If provided, section references it.
               If None, uses generic language.
        backend: The runtime backend ("claude" or "acp"). Defaults to "claude".

    Returns:
        A Markdown section (string) as a self-contained checklist.

    Raises:
        ValueError: If backend is not a recognized value.
    """
    if backend not in ("claude", "acp"):
        raise ValueError(f"backend must be 'claude' or 'acp', got {backend!r}")

    # Determine the prompt file for the backend
    prompt_file = "CLAUDE.md" if backend == "claude" else "AGENTS.md"

    # Build agent reference for personalization
    if agent:
        agent_ref = f"**{agent}**"
        agent_desc = f"your agent ({agent})"
        repo_ref = "your repository"
    else:
        agent_ref = "your agent"
        agent_desc = "your new sibling agent"
        repo_ref = "your repository"

    section = f"""## Establish Agent Identity

For {agent_desc} to be recognized by `steward doctor`, you must establish its
identity in the AgentCulture mesh. This involves two steps:

### 1. Declare the Agent in `culture.yaml`

Create or update `culture.yaml` in {repo_ref} with the following structure:

```yaml
agents:
- suffix: {agent if agent else "<agent-name>"}
  backend: {backend}
```

The `suffix` is the agent's identity in the mesh (used by Culture IRC and mesh
services). The `backend` specifies the runtime platform.

### 2. Create the Matching Prompt File

For **`backend: {backend}`**, the prompt file must be **`{prompt_file}`**.

- Create `{prompt_file}` in the root of {repo_ref}
- This file contains the system prompt for {agent_ref}
- The mapping is fixed by `steward doctor`:
  - `backend: claude` requires `CLAUDE.md`
  - `backend: acp` requires `AGENTS.md`

### Why This Matters

These two files establish the **identity invariants** that `steward doctor`
verifies:

- **prompt-file-present**: {repo_ref} declares an agent in `culture.yaml` and
  has the matching prompt file on disk.
- **backend-consistency**: The declared `backend` in `culture.yaml` matches the
  prompt file present (e.g., `claude` backend with `CLAUDE.md`).

Once `culture.yaml` and `{prompt_file}` are in place, {agent_desc} can be
onboarded into the mesh and will pass these checks."""

    return section
