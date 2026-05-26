"""Dry-run ProvisionPlan: compose manifest + kit + identity + ledger-diff.

``build(agent, desc, backend, root, workspace_root)`` produces a
:class:`ProvisionPlan` dataclass that is the central "what would I do?" object
for ``guild create``.  It is consumed by the executor (t6) and the command
wiring (t7).

**PURITY CONTRACT** — ``build`` and all render methods perform:

* zero subprocess calls
* zero network calls
* zero file *writes*

Reading skill files (via :func:`guild.scaffold.kit.copy_plan`) and the ledger
file (via :func:`guild.cli._commands._broadcast.read_ledger`) is allowed —
those are reads, not mutations.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path

from guild.cli._commands._broadcast import read_ledger
from guild.scaffold import identity as _identity
from guild.scaffold import manifest as _manifest
from guild.scaffold.kit import copy_plan as _copy_plan
from guild.skills import ledger as _ledger

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

__all__ = ["ProvisionPlan", "build"]


@dataclass
class ProvisionPlan:
    """Immutable view of everything ``guild create`` would do.

    Fields
    ------
    repo_spec : dict[str, str]
        Metadata for the to-be-created repo:
        ``agent``, ``desc``, ``backend``, ``visibility``, ``license``,
        ``clone_dest`` (absolute path string).

    manifest : dict[str, str]
        Union of the afi-cli scaffold files (:func:`guild.scaffold.manifest.build`)
        and the identity files (:func:`guild.scaffold.identity.build`).
        Keys are POSIX-style repo-relative paths; values are file contents.

    kit_dests : list[str]
        Planned destination relative paths for every canonical skill file that
        would be copied into ``.claude/skills/<name>/`` of the new repo.
        e.g. ``[".claude/skills/cicd/SKILL.md", ...]``.

    ledger_diff : str
        Unified diff of ``docs/skill-sources.md`` before and after registering
        the new agent as a consumer.  Empty string when the ledger has no
        Downstream column yet (pre-cutover).

    Methods
    -------
    render_human() -> str
        Human-readable dry-run summary, safe to print to a terminal.

    to_dict() -> dict
        JSON-serialisable representation; suitable as a ``--json`` payload.
    """

    repo_spec: dict[str, str]
    manifest: dict[str, str]
    kit_dests: list[str]
    ledger_diff: str = field(default="")

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_human(self) -> str:
        """Return a human-readable dry-run summary."""
        rs = self.repo_spec
        agent = rs["agent"]
        bare = agent.rsplit("/", 1)[-1]

        lines: list[str] = [
            f"DRY-RUN — provision plan for {agent}  (--apply to execute)",
            "",
            "── repo spec ──",
            f"  agent      : {agent}",
            f"  description: {rs['desc']}",
            f"  backend    : {rs['backend']}",
            f"  visibility : {rs['visibility']}",
            f"  license    : {rs['license']}",
            f"  clone_dest : {rs['clone_dest']}",
            "",
            f"── scaffold manifest ({len(self.manifest)} files) ──",
        ]

        for relpath in sorted(self.manifest):
            lines.append(f"  {relpath}")

        lines += [
            "",
            f"── kit copy plan ({len(self.kit_dests)} files → .claude/skills/) ──",
        ]
        # Group by skill name for compact display
        skill_names: list[str] = []
        seen_skills: set[str] = set()
        for dest in sorted(self.kit_dests):
            # dest format: .claude/skills/<name>/...
            parts = dest.split("/")
            if len(parts) >= 3:
                skill_name = parts[2]
                if skill_name not in seen_skills:
                    seen_skills.add(skill_name)
                    skill_names.append(skill_name)
        for sname in sorted(skill_names):
            count = sum(1 for d in self.kit_dests if d.startswith(f".claude/skills/{sname}/"))
            lines.append(f"  .claude/skills/{sname}/  ({count} files)")

        lines += [
            "",
            "── ledger diff (docs/skill-sources.md) ──",
            self.ledger_diff or f"(no change — {bare} not yet in ledger or no Downstream column)",
        ]

        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict representation."""
        return {
            "dry_run": True,
            "repo_spec": dict(self.repo_spec),
            "manifest": {k: v for k, v in self.manifest.items()},
            "kit_dests": list(self.kit_dests),
            "kit_size": len(self.kit_dests),
            "ledger_diff": self.ledger_diff,
        }

    def render_json(self) -> str:
        """Return the JSON-serialised form of :meth:`to_dict`."""
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build(
    agent: str,
    desc: str,
    backend: str,
    root: Path | None,
    workspace_root: Path | None,
) -> ProvisionPlan:
    """Compose a :class:`ProvisionPlan` from the four scaffold primitives.

    Parameters
    ----------
    agent:
        Target agent in ``owner/repo`` or bare-name form.
    desc:
        Short one-line description.
    backend:
        Culture backend (``"claude"`` or ``"acp"``).
    root:
        The guildmaster repo root.  Used to enumerate canonical skills via
        :func:`guild.scaffold.kit.copy_plan` and to read the ledger.
        When ``None`` the repo root is resolved automatically via
        :func:`guild.cli._repo.repo_root`.
    workspace_root:
        The resolved workspace root directory where the new sibling repo
        would be cloned.  This is the already-resolved destination — the
        caller is responsible for applying the three-precedence rule (see
        :mod:`guild.scaffold.workspace`).  When ``None``, defaults to
        ``root.parent``.

    Returns
    -------
    ProvisionPlan
        A fully composed, immutable plan.  Nothing is written to disk.

    Raises
    ------
    ValueError
        If *backend* is unsupported (propagated from
        :func:`guild.scaffold.identity.build`).
    """
    # Resolve root if not supplied
    if root is None:
        from guild.cli._repo import repo_root as _repo_root

        root = _repo_root()

    root = Path(root)

    # Resolve workspace_root
    if workspace_root is None:
        workspace_root = root.parent
    workspace_root = Path(workspace_root)

    # --- Bare name (used for clone dest + ledger diff) ---
    bare = agent.rsplit("/", 1)[-1]

    # --- repo_spec ---
    clone_dest = workspace_root / bare
    repo_spec: dict[str, str] = {
        "agent": agent,
        "desc": desc,
        "backend": backend,
        "visibility": "public",
        "license": "MIT",
        "clone_dest": str(clone_dest),
    }

    # --- manifest: scaffold ∪ identity ---
    scaffold_files = _manifest.build(agent, desc, backend)
    identity_files = _identity.build(agent, desc, backend)
    # Merge: identity takes precedence for overlapping keys (e.g. culture.yaml)
    merged_manifest: dict[str, str] = {}
    merged_manifest.update(scaffold_files)
    merged_manifest.update(identity_files)

    # --- kit_dests: destination relative paths from copy_plan ---
    kit_plan = _copy_plan(root)  # dict[abs_src_str -> dest_relpath_str]
    kit_dests: list[str] = sorted(kit_plan.values())

    # --- ledger_diff ---
    ledger_text = read_ledger(root)
    new_ledger = _ledger.register_consumer(ledger_text, bare)
    ledger_diff = "".join(
        difflib.unified_diff(
            ledger_text.splitlines(keepends=True),
            new_ledger.splitlines(keepends=True),
            fromfile="docs/skill-sources.md",
            tofile="docs/skill-sources.md (after create)",
        )
    )

    return ProvisionPlan(
        repo_spec=repo_spec,
        manifest=merged_manifest,
        kit_dests=kit_dests,
        ledger_diff=ledger_diff,
    )
