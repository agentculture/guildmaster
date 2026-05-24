"""Dogfood the skills-convention invariant before steward's doctor does.

Mirrors steward doctor's ``skills-convention`` check: every
``.claude/skills/<name>/`` has a ``SKILL.md`` whose frontmatter ``name`` equals
the directory name, plus a sibling ``scripts/`` directory.
"""

from __future__ import annotations

from pathlib import Path

from guild.cli._repo import _parse_frontmatter

SKILLS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills"


def test_skills_directory_present() -> None:
    assert SKILLS_DIR.is_dir(), "expected vendored skills under .claude/skills/"


def test_every_skill_matches_convention() -> None:
    skill_dirs = [d for d in SKILLS_DIR.iterdir() if d.is_dir()]
    assert skill_dirs, "no skill directories found"
    for d in skill_dirs:
        skill_md = d / "SKILL.md"
        assert skill_md.is_file(), f"{d.name}: missing SKILL.md"
        assert (d / "scripts").is_dir(), f"{d.name}: missing scripts/ directory"
        fm = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        assert (
            fm.get("name") == d.name
        ), f"{d.name}: frontmatter name {fm.get('name')!r} != dir {d.name!r}"


def test_canonical_set_is_vendored() -> None:
    expected = {
        "cicd",
        "communicate",
        "version-bump",
        "run-tests",
        "sonarclaude",
        "doc-test-alignment",
        "pypi-maintainer",
    }
    present = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
    assert expected <= present, f"missing canonical skills: {expected - present}"
