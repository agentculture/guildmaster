"""Tests for guild.skills.sources — script_list and changelog_excerpt.

TDD: tests are written first to pin the acceptance criteria.
"""

from __future__ import annotations

import pytest

from guild.skills.sources import changelog_excerpt, script_list

# ---------------------------------------------------------------------------
# Fixture: a Keep-a-Changelog string with 3 version blocks
# ---------------------------------------------------------------------------

CHANGELOG = """\
# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-05-20

### Added

- Added the widget module for cicd integration.
- Another cicd-related improvement.

## [0.2.0] - 2026-05-10

### Changed

- Refactored ledger module.
- Improved output formatting.

## [0.1.0] - 2026-05-01

### Added

- Initial release.
- Basic cicd scaffolding.
"""


# ===========================================================================
# script_list
# ===========================================================================


def test_script_list_returns_sorted_files(tmp_path):
    """Top-level files under scripts/ are returned in sorted order."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "z_entry.sh").write_text("#!/bin/bash\n")
    (scripts / "a_helper.py").write_text("# helper\n")
    (scripts / "m_runner.sh").write_text("#!/bin/bash\n")

    result = script_list(tmp_path)
    assert result == ["a_helper.py", "m_runner.sh", "z_entry.sh"]


def test_script_list_skips_subdirectories(tmp_path):
    """Subdirectories (e.g. templates/) are excluded from the result."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run.sh").write_text("#!/bin/bash\n")
    (scripts / "bump.py").write_text("# bump\n")
    templates = scripts / "templates"
    templates.mkdir()
    (templates / "issue.md").write_text("# template\n")

    result = script_list(tmp_path)
    assert "templates" not in result
    assert result == ["bump.py", "run.sh"]


def test_script_list_missing_scripts_dir_returns_empty(tmp_path):
    """If skill_dir/scripts/ does not exist, return []."""
    result = script_list(tmp_path)
    assert result == []


def test_script_list_empty_scripts_dir(tmp_path):
    """An empty scripts/ dir returns []."""
    (tmp_path / "scripts").mkdir()
    result = script_list(tmp_path)
    assert result == []


def test_script_list_accepts_string_path(tmp_path):
    """skill_dir may be supplied as a plain string."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "go.sh").write_text("#!/bin/bash\n")

    result = script_list(str(tmp_path))
    assert result == ["go.sh"]


# ===========================================================================
# changelog_excerpt — since= mode
# ===========================================================================


def test_changelog_excerpt_since_excludes_target_block():
    """since='0.2.0' returns only the 0.3.0 block (0.2.0 block excluded)."""
    result = changelog_excerpt(CHANGELOG, since="0.2.0")
    assert "## [0.3.0]" in result
    assert "## [0.2.0]" not in result
    assert "## [0.1.0]" not in result


def test_changelog_excerpt_since_oldest_returns_all_but_it():
    """since='0.1.0' returns both 0.3.0 and 0.2.0 blocks."""
    result = changelog_excerpt(CHANGELOG, since="0.1.0")
    assert "## [0.3.0]" in result
    assert "## [0.2.0]" in result
    assert "## [0.1.0]" not in result


def test_changelog_excerpt_since_raises_when_version_absent():
    """since='9.9.9' raises ValueError because that heading is not present."""
    with pytest.raises(ValueError, match="9.9.9"):
        changelog_excerpt(CHANGELOG, since="9.9.9")


def test_changelog_excerpt_since_preserves_content():
    """The returned text contains the actual change content, not just headings."""
    result = changelog_excerpt(CHANGELOG, since="0.2.0")
    assert "widget module" in result


# ===========================================================================
# changelog_excerpt — skill= mode (no since)
# ===========================================================================


def test_changelog_excerpt_skill_filters_blocks():
    """Only blocks mentioning the skill name (case-insensitive) are returned."""
    result = changelog_excerpt(CHANGELOG, skill="cicd")
    assert "## [0.3.0]" in result
    # 0.2.0 block does not mention cicd
    assert "## [0.2.0]" not in result
    # 0.1.0 block mentions cicd scaffolding
    assert "## [0.1.0]" in result


def test_changelog_excerpt_skill_case_insensitive():
    """Skill matching is case-insensitive."""
    result_lower = changelog_excerpt(CHANGELOG, skill="cicd")
    result_upper = changelog_excerpt(CHANGELOG, skill="CICD")
    assert result_lower == result_upper


def test_changelog_excerpt_skill_no_match_returns_empty():
    """If the skill is not mentioned in any block, return an empty string."""
    result = changelog_excerpt(CHANGELOG, skill="nonexistent_skill_xyz")
    assert result == ""


# ===========================================================================
# changelog_excerpt — no skill, no since
# ===========================================================================


def test_changelog_excerpt_no_args_returns_whole_changelog():
    """With neither skill nor since, the full changelog text is returned."""
    result = changelog_excerpt(CHANGELOG)
    assert "## [0.3.0]" in result
    assert "## [0.2.0]" in result
    assert "## [0.1.0]" in result
