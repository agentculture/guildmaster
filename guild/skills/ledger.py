"""Ledger helpers for guildmaster's supplier surface.

Operates on the **text** of ``docs/skill-sources.md`` (a Markdown file with
GitHub-flavoured tables) so every function is unit-testable against fixture
strings without touching the live file.

A "supplier table" is identified by a header row that contains a column whose
header text includes the word "Downstream" (case-insensitive) and a "Skill"
column.  Tables that lack either column are ignored.

Public API
----------
parse_consumers(ledger_text, skill) -> list[str]
    Return the de-duplicated, order-preserved list of repo names that consume
    *skill*, drawn from the Downstream column of every matching row.

register_consumer(ledger_text, agent, skills=None) -> str
    Return new ledger text in which *agent* (rendered as a backtick-quoted
    token) is appended to the Downstream cell of every matching row.
    Idempotent: a second call on the result produces byte-identical output.
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_BACKTICK_RE = re.compile(r"`([^`]+)`")


def _parse_tables(ledger_text: str) -> list[dict]:
    """Parse *ledger_text* into a list of table descriptors.

    Each descriptor is a dict::

        {
            "skill_col":      int,   # 0-based column index for the Skill column
            "downstream_col": int,   # 0-based column index for the Downstream column
            "rows": [
                {
                    "line_no": int,          # 0-based index into *lines*
                    "cells":   list[str],    # stripped cell values (not including leading/trailing |)
                },
                ...
            ],
        }

    Only tables that have *both* a "Skill" column and a "Downstream" column
    (case-insensitive match on the header) are returned.
    """
    lines = ledger_text.splitlines(keepends=True)
    tables: list[dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n\r")

        # A GFM table header row: starts and ends with | and has at least two |
        if line.startswith("|") and line.count("|") >= 2:
            header_cells = _split_cells(line)
            # Next line must be the separator row (dashes)
            if i + 1 < len(lines):
                sep = lines[i + 1].rstrip("\n\r")
                if sep.startswith("|") and all(
                    re.fullmatch(r"\s*:?-+:?\s*", c) for c in _split_cells(sep) if c.strip()
                ):
                    # Valid GFM table — locate Skill and Downstream columns
                    skill_col = _find_col(header_cells, "skill")
                    downstream_col = _find_col(header_cells, "downstream")

                    if skill_col is not None and downstream_col is not None:
                        # Collect data rows (everything after the separator until
                        # a line that is not a table row)
                        data_rows = []
                        j = i + 2
                        while j < len(lines):
                            row_line = lines[j].rstrip("\n\r")
                            if not row_line.startswith("|"):
                                break
                            cells = _split_cells(row_line)
                            data_rows.append({"line_no": j, "cells": cells})
                            j += 1

                        tables.append(
                            {
                                "skill_col": skill_col,
                                "downstream_col": downstream_col,
                                "rows": data_rows,
                            }
                        )
                        i = j
                        continue
        i += 1

    return tables


def _find_col(cells: list[str], keyword: str) -> Optional[int]:
    """Return the 0-based index of the first cell whose text contains *keyword*
    (case-insensitive), or *None* if not found."""
    kw = keyword.lower()
    for idx, cell in enumerate(cells):
        if kw in cell.strip().lower():
            return idx
    return None


def _split_cells(row: str) -> list[str]:
    """Split a GFM table row into stripped cell strings.

    Leading and trailing ``|`` are removed; interior ``|`` act as delimiters.
    """
    # Strip outer pipes then split
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def _backtick_names(cell: str) -> list[str]:
    """Return all backtick-quoted names found in *cell*, in order."""
    return _BACKTICK_RE.findall(cell)


def _is_no_consumer(chunk: str) -> bool:
    """Return True if *chunk* represents 'no consumer' (em-dash, hyphen, or blank)."""
    s = chunk.strip()
    return s in ("", "—", "-")


def _parse_downstream_consumers(cell: str) -> list[str]:
    """Parse the Downstream *cell* value into an order-preserved, de-duplicated list
    of bare repo names.

    Rules:
    - Split cell by comma.
    - For each chunk: if it is an em-dash, hyphen, or empty → skip.
    - Otherwise take the *first* backtick-quoted token as the repo name.
    - A chunk with no backtick token is skipped.
    - De-duplicate preserving order of first appearance.
    """
    seen: dict[str, None] = {}  # ordered set via insertion-ordered dict
    for chunk in cell.split(","):
        if _is_no_consumer(chunk):
            continue
        names = _backtick_names(chunk)
        if not names:
            continue
        name = names[0]
        if name not in seen:
            seen[name] = None
    return list(seen)


def _skill_in_cell(skill: str, skill_cell: str) -> bool:
    """Return True if *skill* appears as a backtick-quoted token in *skill_cell*."""
    return skill in _backtick_names(skill_cell)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_consumers(ledger_text: str, skill: str) -> list[str]:
    """Return the de-duplicated, order-preserved list of consumer repo names for *skill*.

    Searches every supplier table (a GFM table with both a "Skill" column and a
    "Downstream" column) for rows whose Skill cell contains `` `skill` `` as a
    backtick-quoted token.  From those rows' Downstream cell the function
    comma-splits and takes the first backtick-quoted token per chunk; em-dashes,
    hyphens, and empty chunks are skipped.

    Parameters
    ----------
    ledger_text:
        Full text of the ledger Markdown file.
    skill:
        Bare skill name to look up (e.g. ``"cicd"``).

    Returns
    -------
    list[str]
        De-duplicated, order-preserved list of bare repo names.  Empty list if
        the skill is not found or has no consumers.

    Raises
    ------
    ValueError
        If *skill* is an empty string.
    """
    if not skill:
        raise ValueError("skill must be a non-empty string")

    seen: dict[str, None] = {}

    for table in _parse_tables(ledger_text):
        skill_col = table["skill_col"]
        downstream_col = table["downstream_col"]

        for row in table["rows"]:
            cells = row["cells"]
            # Guard against rows with too few cells
            if skill_col >= len(cells) or downstream_col >= len(cells):
                continue
            skill_cell = cells[skill_col]
            if not _skill_in_cell(skill, skill_cell):
                continue
            downstream_cell = cells[downstream_col]
            for name in _parse_downstream_consumers(downstream_cell):
                if name not in seen:
                    seen[name] = None

    return list(seen)


def register_consumer(
    ledger_text: str,
    agent: str,
    skills: list[str] | None = None,
) -> str:
    """Return new ledger text with *agent* appended to the Downstream cell of
    every matching row.

    A row matches when its Skill cell contains at least one of the names in
    *skills* (as a backtick-quoted token).  If *skills* is ``None``, every row
    in every supplier table is a candidate.

    **Idempotent**: if `` `agent` `` is already present in a row's Downstream
    cell, that cell is left unchanged.  Calling this function twice on the same
    text produces byte-identical output.

    The Downstream cell is updated in-place; all other text (prose, headings,
    non-supplier tables, column separators, other cells) is preserved exactly.

    Parameters
    ----------
    ledger_text:
        Full text of the ledger Markdown file.
    agent:
        Bare repo / agent name to add (e.g. ``"newsib"``).
    skills:
        Optional list of skill names to restrict the update to.  ``None`` means
        "all rows in supplier tables".

    Returns
    -------
    str
        New ledger text (may be identical to *ledger_text* if already registered).

    Raises
    ------
    ValueError
        If *agent* is an empty string.
    """
    if not agent:
        raise ValueError("agent must be a non-empty string")

    agent_token = f"`{agent}`"

    # Work on a mutable list of lines so we can do targeted replacements.
    lines = ledger_text.splitlines(keepends=True)

    for table in _parse_tables(ledger_text):
        skill_col = table["skill_col"]
        downstream_col = table["downstream_col"]

        for row in table["rows"]:
            cells = row["cells"]
            if skill_col >= len(cells) or downstream_col >= len(cells):
                continue

            skill_cell = cells[skill_col]

            # Decide whether this row is targeted
            if skills is not None:
                if not any(_skill_in_cell(s, skill_cell) for s in skills):
                    continue
            # skills is None → all rows are targeted

            downstream_cell = cells[downstream_col]

            # Idempotency check: skip if already registered
            if agent in _backtick_names(downstream_cell):
                continue

            # Build new cell value
            new_cell = _append_agent_to_cell(downstream_cell, agent_token)

            # Reconstruct the line with the updated downstream cell
            line_no = row["line_no"]
            original_line = lines[line_no]
            lines[line_no] = _replace_cell_in_line(original_line, downstream_col, new_cell)

    return "".join(lines)


def _append_agent_to_cell(cell: str, agent_token: str) -> str:
    """Return a new cell value with *agent_token* appended.

    If the cell currently holds only an em-dash, a hyphen, or is blank, the
    result is just *agent_token* (replacing the placeholder).  Otherwise the
    agent is appended with a comma-space separator.
    """
    stripped = cell.strip()
    if stripped in ("", "—", "-"):
        return agent_token
    return f"{stripped}, {agent_token}"


def _replace_cell_in_line(line: str, col_index: int, new_cell_value: str) -> str:
    """Return *line* with the cell at *col_index* replaced by *new_cell_value*.

    Preserves the line's trailing newline characters.  The replacement is done
    by splitting on ``|``, updating the indexed segment, and re-joining.  The
    leading/trailing ``|`` are kept so the table structure is valid GFM.
    """
    # Preserve trailing newline
    trailing = ""
    for ch in reversed(line):
        if ch in ("\n", "\r"):
            trailing = ch + trailing
        else:
            break

    stripped_line = line.rstrip("\n\r")

    # Split into segments (the leading/trailing | produce empty first/last segments)
    parts = stripped_line.split("|")
    # parts[0] is "" (before the first |)
    # parts[-1] is "" or whitespace (after the last |)
    # data cells are parts[1:-1] (0-indexed)
    data_index = col_index + 1  # offset by the leading empty segment
    if data_index < len(parts):
        # Preserve leading/trailing spaces of the original cell segment for alignment
        original_segment = parts[data_index]
        leading_spaces = len(original_segment) - len(original_segment.lstrip())
        trailing_spaces = len(original_segment) - len(original_segment.rstrip())
        parts[data_index] = (
            " " * leading_spaces + new_cell_value + " " * trailing_spaces
        )

    return "|".join(parts) + trailing
