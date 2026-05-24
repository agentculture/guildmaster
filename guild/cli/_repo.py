"""Filesystem helpers shared by guild's read-only commands.

These resolve the enclosing repo, its ``culture.yaml`` agent declaration, and
the vendored skills under ``.claude/skills/``. Everything here is pure and
offline — no network, no shelling out — so the agent-affordance verbs
(``whoami`` / ``learn`` / ``explain``) stay deterministic and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def find_git_root(start: Path | None = None) -> Path | None:
    """Return the nearest enclosing directory containing ``.git`` (or None).

    Walks up from ``start`` (default: cwd) but never past the filesystem root.
    Bounding lookups to the git checkout keeps a command from picking up an
    ancestor directory outside the user's current repo.
    """
    base = (start or Path.cwd()).resolve()
    for directory in (base, *base.parents):
        if (directory / ".git").exists():
            return directory
    return None


def repo_root(start: Path | None = None) -> Path:
    """Best-effort repo root: the git root if there is one, else cwd."""
    base = (start or Path.cwd()).resolve()
    return find_git_root(base) or base


def load_culture_yaml(root: Path) -> dict[str, Any] | None:
    """Parse ``<root>/culture.yaml`` into a dict, or None if absent/empty.

    Raises nothing on malformed YAML beyond what ``yaml.safe_load`` raises;
    callers that want graceful degradation should guard the call.
    """
    path = root / "culture.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def declared_agents(root: Path) -> list[dict[str, Any]]:
    """Return the ``agents:`` list from ``culture.yaml`` (empty if none)."""
    data = load_culture_yaml(root)
    if not data:
        return []
    agents = data.get("agents")
    if not isinstance(agents, list):
        return []
    return [a for a in agents if isinstance(a, dict)]


@dataclass
class Skill:
    """A vendored skill: its directory name plus SKILL.md frontmatter."""

    name: str
    path: Path
    description: str

    @property
    def skill_md(self) -> Path:
        return self.path / "SKILL.md"


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Return the YAML frontmatter block of a markdown file as a dict.

    Frontmatter is the content between a leading ``---`` line and the next
    ``---`` line. Returns ``{}`` when there is no frontmatter or it doesn't
    parse to a mapping.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        block.append(line)
    try:
        data = yaml.safe_load("\n".join(block))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def iter_skills(root: Path) -> list[Skill]:
    """Discover skills under ``<root>/.claude/skills/*/SKILL.md``.

    Sorted by directory name. A skill directory without a ``SKILL.md`` is
    skipped (it isn't a usable skill); frontmatter ``name``/``description``
    fall back to the directory name / empty string when absent.
    """
    skills_dir = root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []
    found: list[Skill] = []
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if not (child.is_dir() and skill_md.is_file()):
            continue
        fm = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = str(fm.get("name") or child.name)
        description = " ".join(str(fm.get("description", "")).split())
        found.append(Skill(name=name, path=child, description=description))
    return found
