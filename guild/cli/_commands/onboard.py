"""``guild onboard`` — welcome a brand-new sibling agent into the mesh.

Onboard is the "new agent" ceremony, built **on the same engine as ``teach``**
(no separate broadcast path):

    onboard X  ==  teach <all-canonical> --new --to X
                   + register X in docs/skill-sources.md
                   + an identity-setup section in the brief
                   + a verification record (the pins X is expected to vendor)

Dry-run by default: it renders the one consolidated issue, the ledger diff it
*would* apply, and the verification record — writing nothing. ``--apply`` files
the issue, writes the ledger (idempotently), and records the pins.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from guild import __version__
from guild.cli._commands import _broadcast
from guild.cli._output import emit_result
from guild.cli._repo import repo_root
from guild.skills import ledger as _ledger
from guild.skills.identity import identity_section
from guild.skills.render import render_issue

_VERIFICATION_DIR = "docs/onboarding"


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "onboard",
        help="Onboard a new sibling: full kit + identity + ledger (dry-run unless --apply).",
        description=(
            "Welcome a brand-new sibling agent. Renders ONE consolidated issue "
            "(every canonical skill as a section, in new framing, with origin "
            "attribution for inbound skills) plus an identity-setup section, "
            "registers the agent in the ledger, and records the pins it should "
            "vendor. Dry-run by default; --apply commits."
        ),
    )
    parser.add_argument(
        "--agent",
        required=True,
        metavar="OWNER/REPO",
        help="The new sibling repo. Bare names get --org.",
    )
    parser.add_argument(
        "--org",
        default="agentculture",
        help="Default org for a bare --agent name (default: agentculture).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="File the issue + write ledger + record pins (default: dry-run).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit a structured JSON payload to stdout."
    )
    parser.set_defaults(func=_handle)


def _verification_record(agent: str, skills: list[str]) -> dict:
    """The pins a freshly-onboarded sibling is expected to vendor."""
    return {
        "agent": agent,
        "guildmaster_version": __version__,
        "kit_size": len(skills),
        "skills": sorted(skills),
    }


def _onboard_body(agent: str, skills: list[str], *, root: Path, ledger_text: str, origins) -> str:
    welcome = (
        f"## Welcome, `{agent}`\n\n"
        "You're being onboarded into the AgentCulture mesh. Vendor the full "
        f"canonical skill kit below ({len(skills)} skills), then set up your "
        "agent identity at the end.\n"
    )
    # Same rendering engine teach uses — a brand-new sibling consumes nothing
    # yet, so every section renders in NEW framing.
    kit = render_issue(agent, skills, root=root, ledger_text=ledger_text, origins=origins)
    identity = identity_section(agent.rsplit("/", 1)[-1], backend="claude")
    return f"{welcome}\n{kit}\n\n{identity}".rstrip() + "\n"


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()
    agent = _broadcast.normalize_target(args.agent, args.org)
    agent_bare = agent.rsplit("/", 1)[-1]
    skills = _broadcast.canonical_skills(root)
    origins = _broadcast.origins_for(skills)
    ledger_text = _broadcast.read_ledger(root)

    body = _onboard_body(agent, skills, root=root, ledger_text=ledger_text, origins=origins)
    title = f"Onboarding {agent}: vendor the guildmaster skill kit ({len(skills)} skills)"

    new_ledger = _ledger.register_consumer(ledger_text, agent_bare, skills)
    ledger_diff = "".join(
        difflib.unified_diff(
            ledger_text.splitlines(keepends=True),
            new_ledger.splitlines(keepends=True),
            fromfile="docs/skill-sources.md",
            tofile="docs/skill-sources.md (after onboard)",
        )
    )
    verification = _verification_record(agent, skills)

    if args.apply:
        _broadcast.post_issue(root, agent, title, body)
        ledger_written = new_ledger != ledger_text
        if ledger_written:
            (Path(root) / _broadcast.LEDGER_PATH).write_text(new_ledger, encoding="utf-8")
        ver_dir = Path(root) / _VERIFICATION_DIR
        ver_dir.mkdir(parents=True, exist_ok=True)
        ver_path = ver_dir / f"{agent_bare}.json"
        ver_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
        result = {
            "applied": True,
            "agent": agent,
            "posted": agent,
            "ledger_written": ledger_written,
            "verification_path": str(ver_path.relative_to(root)),
        }
    else:
        result = {
            "applied": False,
            "dry_run": True,
            "agent": agent,
            "issue": {"repo": agent, "title": title, "body": body},
            "ledger_diff": ledger_diff,
            "verification": verification,
        }

    emit_result(json.dumps(result, indent=2) if args.json else _render_human(result))
    return 0


def _render_human(result: dict) -> str:
    if result["applied"]:
        return (
            f"Onboarded {result['agent']}: issue filed; "
            f"ledger {'updated' if result['ledger_written'] else 'unchanged'}; "
            f"pins recorded at {result['verification_path']}."
        )
    issue = result["issue"]
    lines = [
        f"DRY-RUN — onboarding {result['agent']}, nothing posted/written. Use --apply.",
        "",
        f"── issue → {issue['repo']} ──",
        issue["title"],
        "",
        issue["body"],
        "── ledger diff (would apply) ──",
        result["ledger_diff"] or "(no change — ledger has no downstream column yet)",
        "",
        "── verification record (would write) ──",
        json.dumps(result["verification"], indent=2),
    ]
    return "\n".join(lines)
