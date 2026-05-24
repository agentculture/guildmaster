"""Filesystem helpers shared by guild's read-only commands.

These resolve the enclosing repo, its ``culture.yaml`` agent declaration, and
the vendored skills under ``.claude/skills/``. Everything here is pure and
offline — no network, no shelling out — so the agent-affordance verbs
(``whoami`` / ``learn`` / ``explain``) stay deterministic and testable.
"""

from __future__ import annotations

import hashlib
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
        # Tolerate an unreadable / non-UTF-8 SKILL.md (skip the skill) — the mesh
        # survey reads SKILL.md across arbitrary external repos, so one bad file
        # must not crash the whole listing.
        try:
            text = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _parse_frontmatter(text)
        name = str(fm.get("name") or child.name)
        description = " ".join(str(fm.get("description", "")).split())
        found.append(Skill(name=name, path=child, description=description))
    return found


@dataclass
class DiscoveredAgent:
    """One Culture agent found while surveying the workspace: its ``suffix``,
    declared ``backend``, and the repo directory it lives in."""

    suffix: str
    backend: str
    repo_path: Path

    @property
    def repo_name(self) -> str:
        return self.repo_path.name


def _agent_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Agent dicts inside a parsed ``culture.yaml`` — both shapes the mesh uses.

    Either an ``agents:`` list (multi-agent repos like culture/daria) or a flat
    root-level ``suffix:``/``backend:`` (single-agent repos). Mirrors steward's
    ``_corpus._extract_agent_entries`` (cite-don't-import).
    """
    if not isinstance(data, dict):
        return []
    if "suffix" in data and "agents" not in data:
        return [data]
    agents = data.get("agents")
    return [a for a in agents if isinstance(a, dict)] if isinstance(agents, list) else []


def discover_agents(
    workspace_root: Path, *, skip_repos: set[str] | None = None
) -> list[DiscoveredAgent]:
    """Discover Culture agents declared in sibling repos under *workspace_root*.

    Globs ``<workspace_root>/*/culture.yaml`` (one level deep — sibling repos,
    not nested manifests) and returns one :class:`DiscoveredAgent` per agent
    entry, sorted by repo name then suffix. Mirrors steward's
    ``_corpus.discover_agents`` (cite-don't-import), trimmed to the inventory
    essentials — no baseline synthesis, scoring, or relationship graph (that
    judgment is steward's lane). Repos whose directory name is in *skip_repos*
    are excluded; unreadable/malformed manifests are skipped (best-effort,
    read-only).
    """
    skip = skip_repos or set()
    agents: list[DiscoveredAgent] = []
    for manifest in sorted(workspace_root.glob("*/culture.yaml")):
        repo_path = manifest.parent
        if repo_path.name in skip:
            continue
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        for entry in _agent_entries(data if isinstance(data, dict) else {}):
            suffix = entry.get("suffix")
            if not suffix:
                continue
            backend_raw = entry.get("backend")
            backend = "" if backend_raw is None else str(backend_raw)
            agents.append(DiscoveredAgent(suffix=str(suffix), backend=backend, repo_path=repo_path))
    return sorted(agents, key=lambda a: (a.repo_name, a.suffix))


def skill_fingerprint(skill_dir: Path) -> str:
    """A deterministic content digest of a skill directory.

    Folds every file under *skill_dir* (sorted by relative path; each file's
    relative path + bytes hashed into one SHA-256) so two copies of a skill
    compare equal iff their tracked content matches — the basis for the
    current/stale signal in ``guild overview --scope mesh``. ``__pycache__`` and
    ``*.pyc`` are skipped (build artifacts, not skill content); **symlinks are
    skipped too** — following them would read content outside the skill dir and
    make the digest non-deterministic. Returns a short 12-char hex digest, or
    ``""`` when the directory is absent or empty.
    """
    if not skill_dir.is_dir():
        return ""
    files = sorted(
        p
        for p in skill_dir.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    )
    if not files:
        return ""
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(skill_dir).as_posix().encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\0")
    return digest.hexdigest()[:12]
