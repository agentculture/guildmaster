"""Source extractors for building per-skill broadcast issue sections.

Functions
---------
script_list(skill_dir)
    Sorted list of top-level file names under ``<skill_dir>/scripts/``.
    Subdirectories (e.g. ``templates/``) are skipped.
    Returns ``[]`` when the ``scripts/`` directory is absent.

changelog_excerpt(changelog_text, *, skill=None, since=None)
    Slice or filter a Keep-a-Changelog formatted string.

    With ``since=X``:
        Return every version block from the top of the file *down to but
        excluding* the ``[X]`` block.  Raises ``ValueError`` when ``[X]``
        is not found (guards against accidentally inlining the whole file).

    Without ``since`` (skill= filter):
        Return only the blocks whose text mentions *skill* (case-insensitive
        substring).  If *skill* is also ``None``, return the whole changelog.
"""

from __future__ import annotations

import re
from pathlib import Path

# Matches a version heading line, e.g. "## [0.3.0] - 2026-05-01"
_HEADING_RE = re.compile(r"^## \[(.+?)\]", re.MULTILINE)


def script_list(skill_dir: "str | Path") -> list[str]:
    """Return sorted top-level file names under ``<skill_dir>/scripts/``.

    Subdirectories are excluded.  Returns ``[]`` when the directory is absent.
    """
    scripts_path = Path(skill_dir) / "scripts"
    if not scripts_path.is_dir():
        return []
    names = [
        entry.name
        for entry in scripts_path.iterdir()
        if entry.is_file()
    ]
    return sorted(names)


def changelog_excerpt(
    changelog_text: str,
    *,
    skill: "str | None" = None,
    since: "str | None" = None,
) -> str:
    """Return a slice or filtered subset of *changelog_text*.

    Parameters
    ----------
    changelog_text:
        Full text of a Keep-a-Changelog formatted file.
    skill:
        When *since* is absent, keep only blocks that mention this string
        (case-insensitive).  ``None`` disables the filter.
    since:
        Return every block from the top of the file down to but **excluding**
        the ``[since]`` block.  Raises ``ValueError`` when the heading is
        absent.
    """
    # Split the changelog into blocks.
    # Each block starts at a "## [X.Y.Z]" heading and runs until the next one.
    matches = list(_HEADING_RE.finditer(changelog_text))

    if not matches:
        # No version blocks at all; return the whole text (or empty).
        return changelog_text

    # Build a list of (version_string, block_text) pairs.
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog_text)
        blocks.append((m.group(1), changelog_text[start:end]))

    # --- since= mode ---
    if since is not None:
        # Verify the target version exists.
        versions = [v for v, _ in blocks]
        if since not in versions:
            raise ValueError(
                f"changelog_excerpt: version [{since}] not found in changelog. "
                f"Available versions: {versions}"
            )
        # Keep all blocks that appear before the [since] block.
        kept: list[str] = []
        for version, text in blocks:
            if version == since:
                break
            kept.append(text)
        return "".join(kept)

    # --- skill= filter mode ---
    if skill is not None:
        needle = skill.lower()
        kept = [text for _, text in blocks if needle in text.lower()]
        return "".join(kept)

    # --- no filter — return everything ---
    return changelog_text
