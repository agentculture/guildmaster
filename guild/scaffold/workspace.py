"""Portable workspace-root resolution for the guild create flow.

Decides WHERE a new sibling repo gets cloned — the workspace root directory —
portably, never embedding a hardcoded home path. Uses three precedence levels:
  1. Explicit --workspace-root flag (if set)
  2. workspace_root key from parsed local config (if present)
  3. repo_root.parent (the directory holding sibling repos)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve(
    repo_root: Path,
    flag: Path | None,
    local_cfg: dict[str, Any] | None,
) -> Path:
    """Resolve the workspace root where a new sibling repo should be cloned.

    Applies three precedence levels:
      1. *flag* (the --workspace-root value) if set
      2. workspace_root key from *local_cfg* (parsed skills.local.yaml) if present
      3. repo_root.parent (the directory holding this repo and its siblings)

    Args:
        repo_root: The guildmaster repo root (a Path).
        flag: The --workspace-root value (a Path or None).
        local_cfg: The parsed skills.local.yaml dict (or None). The
            workspace_root key (if present) is treated as a path string,
            and tilde expansion is applied.

    Returns:
        A pathlib.Path to the workspace root. The result is always derived
        from inputs, never a hardcoded path. No absolute /home/... paths
        are embedded in source; home-dir paths only appear if a config
        value explicitly contains them (user-supplied, via ~-expansion).
    """
    # Branch 1: explicit flag takes precedence
    if flag is not None:
        return flag

    # Branch 2: local config, if workspace_root key is present
    if local_cfg is not None:
        workspace_root = local_cfg.get("workspace_root")
        if workspace_root is not None:
            # Config value is a string; expand ~ if present, then return as Path
            return Path(str(workspace_root)).expanduser()

    # Branch 3: default to repo_root's parent (the workspace holding sibling repos)
    return repo_root.parent
