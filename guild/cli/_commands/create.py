"""``guild create`` — provision a brand-new sibling repo from guildmaster.

Instantiates the GitHub template ``agentculture/culture-agent-template``
(overridable via ``--template``), renames identifiers throughout the clone to
match the new agent name, writes a self-init CLAUDE.md seed, configures the
GitHub repo, pushes the customised genesis commit, and registers the new agent
in ``docs/skill-sources.md``.

Dry-run by default: renders the provision plan (the repo spec, the rename map,
the steps it WOULD run, the ledger diff) and performs NOTHING external.
``--apply`` executes the plan.

Usage
-----
    guild create --agent OWNER/REPO --desc TEXT [--org agentculture]
                 [--backend claude|acp] [--workspace-root DIR]
                 [--template agentculture/culture-agent-template]
                 [--dist NAME] [--apply] [--json]
"""

from __future__ import annotations

import argparse
import difflib
import json
import keyword
import re
from pathlib import Path

from guild.cli._commands import _broadcast
from guild.cli._commands import _provision_template as _provision
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import repo_root
from guild.scaffold.instantiate import transform_plan as _transform_plan
from guild.skills import ledger as _ledger


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "create",
        help="Provision a brand-new sibling repo from the template (dry-run unless --apply).",
        description=(
            "Instantiate ``agentculture/culture-agent-template``, rename "
            "identifiers to match the new agent, write a self-init CLAUDE.md "
            "seed, configure the GitHub repo, push the genesis commit, and "
            "register the agent in docs/skill-sources.md. "
            "Dry-run by default."
        ),
    )
    parser.add_argument(
        "--agent",
        required=True,
        metavar="OWNER/REPO",
        help="The new sibling repo. Bare names get --org prepended.",
    )
    parser.add_argument(
        "--desc",
        required=True,
        metavar="TEXT",
        help="Short description for the new agent (threaded into the repo and the seed).",
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
        help="The new sibling's backend — picks the prompt file (default: claude).",
    )
    parser.add_argument(
        "--workspace-root",
        metavar="DIR",
        type=Path,
        default=None,
        help=(
            "Directory where the new repo will be cloned. "
            "Defaults to the parent of the guildmaster repo root."
        ),
    )
    parser.add_argument(
        "--template",
        metavar="OWNER/REPO",
        default=_provision.DEFAULT_TEMPLATE,
        help=f"GitHub template repo to instantiate (default: {_provision.DEFAULT_TEMPLATE}).",
    )
    parser.add_argument(
        "--dist",
        metavar="NAME",
        default=None,
        help=(
            "PyPI distribution name. Defaults to the repo name; pass e.g. "
            "'jetson-cli' to ship the dist as 'jetson-cli' while keeping the "
            "command and import package as the repo name ('jetson'). Retargets "
            "[project].name, the importlib.metadata lookup, and the TestPyPI pin."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Execute the plan: create the repo from the template, clone, "
            "transform, configure, push genesis commit, register in ledger."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a structured JSON payload to stdout.",
    )
    parser.set_defaults(func=_handle)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def _handle(args: argparse.Namespace) -> None:
    root = repo_root()
    agent = _broadcast.normalize_target(args.agent, args.org)
    bare = agent.rsplit("/", 1)[-1]

    # Fail fast (before any external act) if the repo name can't derive a valid
    # Python package identifier — the derived pkg is both a directory name and a
    # global rename token, so an invalid value (dots, leading digit) breaks the
    # generated sibling.
    pkg = bare.lower().replace("-", "_")
    if not pkg.isidentifier() or keyword.iskeyword(pkg):
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"repo name {bare!r} derives an invalid Python package name {pkg!r}",
            remediation=(
                "use a repo name of letters/digits/hyphens that maps to a valid, "
                "non-keyword Python identifier (e.g. not starting with a digit)"
            ),
        )

    # Validate the optional PyPI dist name (fail fast, before any external act).
    # PyPI normalises [-_.] runs, but the raw name must still be a non-empty run
    # of letters/digits/.-_ that starts and ends alphanumerically (PEP 503).
    if args.dist is not None and not re.match(
        r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$", args.dist
    ):
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"--dist {args.dist!r} is not a valid PyPI distribution name",
            remediation=(
                "use letters/digits/.-_ starting and ending alphanumerically " "(e.g. 'jetson-cli')"
            ),
        )

    # Resolve workspace root (parent of guildmaster if not supplied).
    workspace_root = args.workspace_root if args.workspace_root is not None else root.parent
    clone_dest = workspace_root / bare

    # Build the dry-run plan (pure — no writes, no subprocess).
    plan = _transform_plan(bare, args.desc, dist=args.dist)

    # Ledger diff (pure — reads only).
    skills = _broadcast.canonical_skills(root)
    ledger_text = _broadcast.read_ledger(root)
    new_ledger = _ledger.register_consumer(ledger_text, bare, skills)
    ledger_diff = "".join(
        difflib.unified_diff(
            ledger_text.splitlines(keepends=True),
            new_ledger.splitlines(keepends=True),
            fromfile="docs/skill-sources.md",
            tofile="docs/skill-sources.md (after create)",
        )
    )

    if not args.apply:
        # Dry-run: render and exit — zero external side-effects.
        dry_result = {
            "applied": False,
            "dry_run": True,
            "agent": agent,
            "backend": args.backend,
            "template": args.template,
            "clone_dest": str(clone_dest),
            "plan": plan,
            "ledger_diff": ledger_diff,
        }
        emit_result(json.dumps(dry_result, indent=2) if args.json else _render_dry_run(dry_result))
        return

    # --apply path.
    apply_result = _provision.apply(
        agent=agent,
        bare=bare,
        desc=args.desc,
        backend=args.backend,
        clone_dest=clone_dest,
        guildmaster_root=root,
        template=args.template,
        dist=args.dist,
    )

    # Register in the ledger idempotently.
    ledger_written = new_ledger != ledger_text
    if ledger_written:
        (root / _broadcast.LEDGER_PATH).write_text(new_ledger, encoding="utf-8")

    result = {
        "applied": True,
        "agent": agent,
        "backend": args.backend,
        "template": args.template,
        "repo": apply_result["repo"],
        "clone_dest": apply_result["clone_dest"],
        "pushed": apply_result["pushed"],
        "dist": plan["dist"],
        "ledger_written": ledger_written,
    }
    emit_result(json.dumps(result, indent=2) if args.json else _render_apply(result))


# ---------------------------------------------------------------------------
# Human renderers
# ---------------------------------------------------------------------------


def _render_dry_run(result: dict) -> str:
    plan = result["plan"]
    lines = [
        f"DRY-RUN — guild create {result['agent']}. Use --apply to execute.",
        "",
        f"  template   : {result['template']}",
        f"  agent      : {result['agent']}",
        f"  backend    : {result['backend']}",
        f"  clone dest : {result['clone_dest']}",
        f"  pkg        : {plan['pkg']}",
        f"  repo token : {plan['repo_token']}",
        f"  dist (PyPI): {plan['dist']}"
        + ("" if plan["dist"] == plan["repo_token"] else "  (command + import stay repo token)"),
        "",
        "── rename map ──",
    ]
    for old, new in plan["rename_map"].items():
        lines.append(f"  {old!r} → {new!r}")
    lines += [
        "",
        "── steps (would execute) ──",
    ]
    for i, step in enumerate(plan["steps"], 1):
        lines.append(f"  {i}. {step}")
    lines += [
        "",
        "── ledger diff (would apply) ──",
        result["ledger_diff"] or "(no change — already registered or no supplier table yet)",
    ]
    return "\n".join(lines)


def _render_apply(result: dict) -> str:
    return (
        f"Created {result['agent']}: genesis commit pushed; "
        f"ledger {'updated' if result['ledger_written'] else 'unchanged'}."
    )
