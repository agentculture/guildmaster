"""Tests for guild.scaffold.kit — kit-copy planner.

Acceptance criteria:
1. copy_plan(root) returns a src->dest mapping covering every canonical skill
   (iter_skills minus SELF_SKILLS), with destinations under .claude/skills/<name>/...
2. Each planned skill dir, when copied, is byte-identical to guildmaster's own copy
   (excluding any file named skills.local.yaml); inbound skills retain origin
   attribution in their copied SKILL.md.
"""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path

from guild.cli._commands._broadcast import canonical_skills
from guild.cli._repo import repo_root
from guild.scaffold.kit import copy_plan
from guild.skills import INBOUND_ORIGINS, SELF_SKILLS

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

WORKTREE_ROOT = repo_root(Path(__file__).parent)


def _all_skill_files(skill_dir: Path) -> list[Path]:
    """Recursively list all non-excluded files under a skill directory."""
    return sorted(p for p in skill_dir.rglob("*") if p.is_file() and p.name != "skills.local.yaml")


# ---------------------------------------------------------------------------
# criterion 1: copy_plan returns the right key/value shape
# ---------------------------------------------------------------------------


class TestCopyPlanShape:
    def test_returns_a_mapping(self):
        plan = copy_plan(WORKTREE_ROOT)
        assert isinstance(plan, dict), "copy_plan must return a dict"

    def test_covers_every_canonical_skill(self):
        plan = copy_plan(WORKTREE_ROOT)
        expected_skills = set(canonical_skills(WORKTREE_ROOT))
        # Gather skill names represented in the plan (by destination prefix)
        dest_skill_names = {Path(dest).parts[2] for dest in plan.values()}
        assert (
            expected_skills == dest_skill_names
        ), f"plan skill names {dest_skill_names} != canonical {expected_skills}"

    def test_excludes_self_skills(self):
        plan = copy_plan(WORKTREE_ROOT)
        dest_skill_names = {Path(dest).parts[2] for dest in plan.values()}
        for self_skill in SELF_SKILLS:
            assert (
                self_skill not in dest_skill_names
            ), f"SELF_SKILL '{self_skill}' must not appear in the kit copy plan"

    def test_destinations_under_dot_claude_skills(self):
        plan = copy_plan(WORKTREE_ROOT)
        for src, dest in plan.items():
            dest_path = Path(dest)
            assert dest_path.parts[0] == ".claude", f"{dest} must start with .claude/"
            assert dest_path.parts[1] == "skills", f"{dest} must be under .claude/skills/"

    def test_source_paths_are_absolute_and_exist(self):
        plan = copy_plan(WORKTREE_ROOT)
        for src in plan:
            src_path = Path(src)
            assert src_path.is_absolute(), f"source path must be absolute: {src}"
            assert src_path.is_file(), f"source file must exist: {src}"

    def test_source_destination_name_consistency(self):
        """Each source file's skill-dir name must match its destination skill-dir name."""
        plan = copy_plan(WORKTREE_ROOT)
        skills_dir = WORKTREE_ROOT / ".claude" / "skills"
        for src, dest in plan.items():
            src_skill_name = Path(src).relative_to(skills_dir).parts[0]
            dest_skill_name = Path(dest).parts[2]
            assert (
                src_skill_name == dest_skill_name
            ), f"src skill '{src_skill_name}' != dest skill '{dest_skill_name}'"

    def test_excludes_skills_local_yaml(self):
        """No entry in the plan should reference a file named skills.local.yaml."""
        plan = copy_plan(WORKTREE_ROOT)
        for src, dest in plan.items():
            assert (
                Path(src).name != "skills.local.yaml"
            ), f"skills.local.yaml must be excluded from the plan (found src: {src})"
            assert (
                Path(dest).name != "skills.local.yaml"
            ), f"skills.local.yaml must be excluded from the plan (found dest: {dest})"

    def test_all_files_under_each_skill_dir_are_covered(self):
        """Every file under each canonical skill dir must appear as a plan source."""
        plan = copy_plan(WORKTREE_ROOT)
        src_set = set(plan.keys())
        skills_dir = WORKTREE_ROOT / ".claude" / "skills"
        canonical = canonical_skills(WORKTREE_ROOT)
        for skill_name in canonical:
            skill_dir = skills_dir / skill_name
            for f in _all_skill_files(skill_dir):
                assert str(f) in src_set, f"file {f} under skill '{skill_name}' missing from plan"


# ---------------------------------------------------------------------------
# criterion 2: byte-identical copy + inbound attribution preserved
# ---------------------------------------------------------------------------


class TestByteIdentityAndAttribution:
    def test_copied_skill_dirs_are_byte_identical(self, tmp_path):
        """Copy the plan into tmp_path; every file must be byte-identical to source."""
        plan = copy_plan(WORKTREE_ROOT)

        # Perform the copy
        for src, dest_rel in plan.items():
            dest = tmp_path / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        # Compare each copied file byte-by-byte with the source
        for src, dest_rel in plan.items():
            dest = tmp_path / dest_rel
            assert dest.is_file(), f"expected copied file at {dest}"
            match, mismatch, errors = filecmp.cmpfiles(
                str(Path(src).parent),
                str(dest.parent),
                [Path(src).name],
                shallow=False,
            )
            assert Path(src).name in match, (
                f"file {dest_rel} is NOT byte-identical to {src} "
                f"(mismatch={mismatch}, errors={errors})"
            )

    def test_inbound_skills_retain_origin_attribution(self, tmp_path):
        """Inbound (devague trio) SKILL.md files must still contain their origin repo string."""
        plan = copy_plan(WORKTREE_ROOT)

        # Copy only the inbound skills
        for src, dest_rel in plan.items():
            dest = tmp_path / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        for skill_name, origin_repo in INBOUND_ORIGINS.items():
            skill_md = tmp_path / ".claude" / "skills" / skill_name / "SKILL.md"
            assert (
                skill_md.is_file()
            ), f"SKILL.md not found for inbound skill '{skill_name}' at {skill_md}"
            content = skill_md.read_text(encoding="utf-8")
            assert origin_repo in content, (
                f"Inbound skill '{skill_name}' SKILL.md does not contain "
                f"origin attribution '{origin_repo}' after copy"
            )
