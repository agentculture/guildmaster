"""Compose per-skill sections into ONE agent-major broadcast issue body.

``teach`` / ``onboard`` file one GitHub issue per *target agent*; this module
builds that issue's body by rendering a section per skill the agent receives.
Each section reuses the shape of the vendored ``communicate`` announce
templates (what's in upstream now: script list; CHANGELOG excerpt; cite
locations; origin block), under a per-skill heading, with new-vs-resync framing
chosen **per (skill, agent)** from the ledger.

The split is deliberate: :func:`render_section` is pure (inputs in, markdown
out, easy to unit-test); :func:`render_issue` integrates the ledger
(framing) + sources (scripts/CHANGELOG) for a whole agent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from guild.skills import ledger as _ledger
from guild.skills import sources as _sources

SKILLS_DIR = ".claude/skills"
CHANGELOG = "CHANGELOG.md"
_CITE_REMOTE = "https://github.com/agentculture/guildmaster/tree/main/.claude/skills"


def _origin_block(skill: str, origin: str | None) -> str:
    if not origin:
        return ""
    return (
        f"> **Origin:** `{skill}` originates in "
        f"[`{origin}`](https://github.com/{origin}); guildmaster only "
        f"re-broadcasts it — cite guildmaster's copy, track `{origin}` as upstream."
    )


def render_section(
    skill: str,
    *,
    scripts: Sequence[str],
    changelog: str = "",
    new: bool = True,
    origin: str | None = None,
) -> str:
    """Render one per-skill section of an agent-major issue body (pure)."""
    framing = (
        f"**New skill — add it fresh.** Your repo does not vendor `{skill}` yet."
        if new
        else f"**Resync.** You already vendor `{skill}`; this updates your copy."
    )
    lines = [f"### `{skill}`", "", framing, ""]
    block = _origin_block(skill, origin)
    if block:
        lines += [block, ""]
    lines += [
        f"Cite: `../guildmaster/{SKILLS_DIR}/{skill}/` "
        f"(remote: <{_CITE_REMOTE}/{skill}>)",
        "",
        f"`{skill}/scripts/` ({len(scripts)} files):",
        "",
    ]
    lines += [f"- `{name}`" for name in scripts] or ["- _(no top-level scripts)_"]
    if changelog.strip():
        lines += ["", "Relevant guildmaster CHANGELOG entries:", "", changelog.strip()]
    lines.append("")
    return "\n".join(lines)


def render_issue(
    agent: str,
    skills: Sequence[str],
    *,
    root: Path,
    ledger_text: str = "",
    since: str | None = None,
    origins: Mapping[str, str] | None = None,
) -> str:
    """Render ONE issue body for *agent* bundling a section per skill.

    Framing per ``(skill, agent)`` is auto-detected from *ledger_text*: an agent
    already listed as a downstream consumer of a skill gets a **resync** section,
    otherwise a **new** section.  *origins* maps a skill to an upstream
    ``owner/repo`` (e.g. the devague trio) for the origin-attribution block.

    Raises ``ValueError`` (via :func:`guild.skills.sources.changelog_excerpt`)
    when *since* names a version absent from ``CHANGELOG.md``.
    """
    origins = origins or {}
    root = Path(root)
    changelog_text = ""
    cl_path = root / CHANGELOG
    if cl_path.is_file():
        changelog_text = cl_path.read_text(encoding="utf-8")

    intro = [
        f"## Skills update for `{agent}` (from guildmaster)",
        "",
        f"guildmaster is propagating {len(skills)} skill(s) to `{agent}`. Each "
        "section below is one skill; framing is per-skill (new vs resync). Apply "
        "each in its own branch.",
        "",
    ]

    sections = []
    for skill in skills:
        consumers = _ledger.parse_consumers(ledger_text, skill) if ledger_text else []
        scripts = _sources.script_list(root / SKILLS_DIR / skill)
        changelog = ""
        if changelog_text:
            changelog = _sources.changelog_excerpt(
                changelog_text, skill=skill, since=since
            )
        sections.append(
            render_section(
                skill,
                scripts=scripts,
                changelog=changelog,
                new=agent not in consumers,
                origin=origins.get(skill),
            )
        )

    return "\n".join(intro + sections).rstrip() + "\n"
