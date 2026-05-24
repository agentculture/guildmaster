"""Shared helpers for the broadcast verbs ``teach`` and ``onboard``.

Posting and git/ledger mutation live in the CLI layer (not ``guild.skills``,
which stays pure). These helpers resolve the canonical skill set, normalize
target repos, read the ledger, and shell out to the vendored ``communicate``
``post-issue.sh`` (which auto-signs from ``culture.yaml`` via ``agtag``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.cli._repo import iter_skills
from guild.skills import INBOUND_ORIGINS, SELF_SKILLS

# Resolve bash to an absolute path so we never invoke a partial executable name.
_BASH = shutil.which("bash") or "/bin/bash"

LEDGER_PATH = "docs/skill-sources.md"
POST_ISSUE = ".claude/skills/communicate/scripts/post-issue.sh"


def canonical_skills(root: Path) -> list[str]:
    """The kit guildmaster supplies: every vendored skill except its own verbs."""
    return [s.name for s in iter_skills(root) if s.name not in SELF_SKILLS]


def normalize_target(name: str, org: str) -> str:
    """``daria`` -> ``agentculture/daria``; an explicit ``owner/repo`` is kept."""
    return name if "/" in name else f"{org}/{name}"


def read_ledger(root: Path) -> str:
    path = Path(root) / LEDGER_PATH
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def origins_for(skills: Iterable[str]) -> dict[str, str]:
    """Origin-attribution map for the subset of *skills* that are inbound."""
    return {s: INBOUND_ORIGINS[s] for s in skills if s in INBOUND_ORIGINS}


def validate_skills(requested: list[str], available: list[str]) -> None:
    """Raise a user error if any requested skill is not in the canonical set."""
    unknown = [s for s in requested if s not in available]
    if unknown:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"unknown skill(s): {', '.join(unknown)}",
            remediation=f"choose from the canonical set: {', '.join(available)}",
        )


def post_issue(root: Path, repo: str, title: str, body: str) -> None:
    """Post one issue via the vendored ``post-issue.sh``; raise on failure."""
    script = Path(root) / POST_ISSUE
    if not script.is_file():
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message=f"post-issue.sh not found at {script}",
            remediation="vendor the 'communicate' skill before posting",
        )
    tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    try:
        tmp.write(body)
        tmp.close()
        proc = subprocess.run(
            [_BASH, str(script), "--repo", repo, "--title", title, "--body-file", tmp.name],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise GuildError(
                code=EXIT_USER_ERROR,
                message=f"posting to {repo} failed: {proc.stderr.strip() or proc.stdout.strip()}",
                remediation="check repo access + agtag auth, then retry",
            )
    finally:
        os.unlink(tmp.name)
