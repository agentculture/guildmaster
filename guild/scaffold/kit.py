"""Kit-copy planner: enumerate every file in guildmaster's canonical skill set.

``copy_plan(root)`` is a pure function — it reads the filesystem and returns a
mapping; it never writes anything. An optional ``apply_plan`` helper performs
the actual copy for callers that need it (e.g. ``guild create --apply``).

Canonical skills = ``iter_skills(root)`` minus ``SELF_SKILLS`` — the same
definition used by ``canonical_skills()`` in the broadcast layer.

The file named ``skills.local.yaml`` is per-machine and git-ignored; it is
excluded from the plan so a vendor copy never accidentally ships a local
override.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from guild.cli._repo import iter_skills
from guild.skills import SELF_SKILLS

# Files that are per-machine and must never be included in a vendor copy.
_EXCLUDED_FILENAMES: frozenset[str] = frozenset({"skills.local.yaml"})


def copy_plan(root: Path) -> dict[str, str]:
    """Return a source-path -> destination-relpath mapping for the canonical skill kit.

    For each canonical skill (``iter_skills(root)`` minus ``SELF_SKILLS``) every
    file under the skill directory is mapped to a destination relative path of
    the form ``.claude/skills/<name>/<relpath>``.

    Keys are absolute path strings (so callers do not need to know *root*).
    Values are relative path strings, using ``/`` as the separator regardless of
    platform (POSIX-style relpaths keep the plan serialisable and
    platform-neutral).

    Files named ``skills.local.yaml`` anywhere under a skill dir are excluded —
    they are per-machine overrides, git-ignored, and must not be vendor-copied.
    """
    plan: dict[str, str] = {}
    skills_dir = root / ".claude" / "skills"

    for skill in iter_skills(root):
        if skill.name in SELF_SKILLS:
            continue
        skill_dir = skill.path
        for file_path in sorted(skill_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name in _EXCLUDED_FILENAMES:
                continue
            rel_within_skill = file_path.relative_to(skills_dir)
            dest_rel = ".claude/skills/" + rel_within_skill.as_posix()
            plan[str(file_path)] = dest_rel

    return plan


def apply_plan(plan: dict[str, str], dest_root: Path) -> None:
    """Copy all files in *plan* into *dest_root*.

    This is a convenience helper — the plan is the core contract; this
    function is just a thin loop over ``shutil.copy2``. Callers that need
    finer control (progress reporting, dry-run checks) should iterate the plan
    themselves.

    Destination directories are created with ``mkdir(parents=True, exist_ok=True)``
    so the caller does not need to pre-create anything.
    """
    for src, dest_rel in plan.items():
        dest = dest_root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
