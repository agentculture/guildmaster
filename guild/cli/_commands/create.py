"""``guild create`` — provision a brand-new sibling repo from guildmaster.

Dry-run by default: renders the :class:`~guild.scaffold.plan.ProvisionPlan`
(human-readable or ``--json``) and exits 0, performing NOTHING external.
``--apply`` runs the full executor then registers the new agent in the
``docs/skill-sources.md`` ledger idempotently.

    guild create --agent OWNER/REPO --desc "..." [--backend claude|acp]
                 [--workspace-root DIR] [--apply] [--json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from guild.cli._commands import _broadcast, _provision
from guild.cli._output import emit_result
from guild.cli._repo import repo_root
from guild.scaffold import plan as _plan
from guild.scaffold import workspace as _workspace
from guild.skills import ledger as _ledger


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "create",
        help="Provision a brand-new sibling repo (dry-run unless --apply).",
        description=(
            "Compose a ProvisionPlan (scaffold manifest + canonical skill kit + "
            "identity files + ledger diff) and, with --apply, execute it: "
            "create the GitHub repo, push the genesis commit, and register the "
            "agent in docs/skill-sources.md. Dry-run by default."
        ),
    )
    parser.add_argument(
        "--agent",
        required=True,
        metavar="OWNER/REPO",
        help="The new sibling repo. Bare names get --org.",
    )
    parser.add_argument(
        "--desc",
        required=True,
        metavar="TEXT",
        help="Short one-line description threaded into the ProvisionPlan and repo.",
    )
    parser.add_argument(
        "--org",
        default="agentculture",
        help="Default org for a bare --agent name (default: agentculture).",
    )
    parser.add_argument(
        "--backend",
        choices=["claude", "acp"],
        default="claude",
        help="The new sibling's backend (default: claude).",
    )
    parser.add_argument(
        "--workspace-root",
        metavar="DIR",
        type=Path,
        default=None,
        help="Directory where the new repo will be cloned (default: repo_root.parent).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the plan: create repo, push genesis commit, register in ledger.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a structured JSON payload to stdout.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()
    agent = _broadcast.normalize_target(args.agent, args.org)
    bare = agent.rsplit("/", 1)[-1]

    # Resolve workspace_root via the three-precedence rule.
    workspace_root = _workspace.resolve(root, args.workspace_root, {})

    # Build the dry-run plan (pure — no writes, no subprocess).
    provision_plan = _plan.build(agent, args.desc, args.backend, root, workspace_root)

    if not args.apply:
        # Dry-run: render and exit without touching anything external.
        output = provision_plan.render_json() if args.json else provision_plan.render_human()
        emit_result(output)
        return 0

    # --apply path: execute the plan (creates repo, pushes genesis commit).
    apply_result = _provision.apply(provision_plan, root=root)

    # Register the new agent in the ledger idempotently.
    skills = _broadcast.canonical_skills(root)
    ledger_text = _broadcast.read_ledger(root)
    new_ledger = _ledger.register_consumer(ledger_text, bare, skills)
    ledger_written = new_ledger != ledger_text
    if ledger_written:
        (Path(root) / _broadcast.LEDGER_PATH).write_text(new_ledger, encoding="utf-8")

    result = {
        "applied": True,
        "agent": agent,
        "backend": args.backend,
        "repo": apply_result["repo"],
        "clone_dest": apply_result["clone_dest"],
        "manifest_files": apply_result["manifest_files"],
        "kit_files": apply_result["kit_files"],
        "pushed": apply_result["pushed"],
        "ledger_written": ledger_written,
    }

    emit_result(json.dumps(result, indent=2) if args.json else _render_human(result))
    return 0


def _render_human(result: dict) -> str:
    if result["applied"]:
        return (
            f"Created {result['agent']}: genesis commit pushed; "
            f"ledger {'updated' if result['ledger_written'] else 'unchanged'}."
        )
    # Should not reach here in practice (dry-run exits early), but kept for completeness.
    return f"DRY-RUN — provision plan for {result.get('agent', '?')}. Use --apply."
