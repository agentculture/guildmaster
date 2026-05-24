"""``guild teach`` — propagate a SET of skills to a SET of mesh agents.

Agent-major: one issue per target agent, bundling a per-skill section for every
taught skill (not one issue per skill). Targeting resolves from ``--to``,
falling back to the ledger's current consumers per skill. **Dry-run by
default**; ``--apply`` files the issues via the vendored ``communicate`` skill.
"""

from __future__ import annotations

import argparse
import json

from guild.cli._commands import _broadcast
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import repo_root
from guild.skills import ledger as _ledger
from guild.skills.render import render_issue


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "teach",
        help="Teach a set of skills to a set of mesh agents (dry-run unless --apply).",
        description=(
            "Propagate a chosen set of skills to a chosen set of mesh agents. "
            "Files one agent-major issue per target (per-skill sections bundled), "
            "with new-vs-resync framing auto-detected per (skill, agent). Dry-run "
            "by default; --apply posts."
        ),
    )
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        metavar="NAME",
        help="A skill to teach (repeatable).",
    )
    parser.add_argument("--all", action="store_true", help="Teach the full canonical skill set.")
    parser.add_argument(
        "--to",
        action="append",
        dest="targets",
        metavar="OWNER/REPO",
        help="Target agent repo (repeatable). Bare names get --org.",
    )
    parser.add_argument(
        "--org",
        default="agentculture",
        help="Default org for bare --to names (default: agentculture).",
    )
    parser.add_argument("--since", metavar="VERSION", help="CHANGELOG cutoff version (exclusive).")
    parser.add_argument(
        "--apply", action="store_true", help="File the issues (default: dry-run, render only)."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit a structured JSON payload to stdout."
    )
    parser.set_defaults(func=_handle)


def _resolve_skills(args: argparse.Namespace, root) -> list[str]:
    available = _broadcast.canonical_skills(root)
    if args.all and args.skills:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message="use either --skill or --all, not both",
            remediation="drop one of --skill / --all",
        )
    if args.all:
        return available
    if args.skills:
        _broadcast.validate_skills(args.skills, available)
        return list(args.skills)
    raise GuildError(
        code=EXIT_USER_ERROR,
        message="no skills selected",
        remediation="pass --skill NAME (repeatable) or --all; there is no implicit default",
    )


def _resolve_targets(args: argparse.Namespace, skills: list[str], ledger_text: str) -> list[str]:
    if args.targets:
        out: list[str] = []
        for t in args.targets:
            norm = _broadcast.normalize_target(t, args.org)
            if norm not in out:
                out.append(norm)
        return out
    # Ledger fallback: the union of current consumers across the selected skills.
    seen: list[str] = []
    for skill in skills:
        for consumer in _ledger.parse_consumers(ledger_text, skill):
            norm = _broadcast.normalize_target(consumer, args.org)
            if norm not in seen:
                seen.append(norm)
    if not seen:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=(
                "no targets: --to not given and the ledger lists no "
                "consumers for the selected skill(s)"
            ),
            remediation="pass --to OWNER/REPO (repeatable)",
        )
    return seen


def _build_issues(targets, skills, *, root, ledger_text, since, origins) -> list[dict]:
    title = f"Skills update from guildmaster: {', '.join(skills)}"
    issues = []
    for target in targets:
        try:
            body = render_issue(
                target, skills, root=root, ledger_text=ledger_text, since=since, origins=origins
            )
        except ValueError as exc:
            raise GuildError(
                code=EXIT_USER_ERROR,
                message=str(exc),
                remediation="pass an existing --since version or omit it",
            ) from exc
        issues.append({"repo": target, "title": title, "body": body})
    return issues


def _render_human(result: dict) -> str:
    if result["applied"]:
        return f"Posted {len(result['posted'])} issue(s): " + ", ".join(result["posted"])
    lines = [
        f"DRY-RUN — {len(result['issues'])} issue(s), nothing posted. Use --apply to file.",
        "",
    ]
    for issue in result["issues"]:
        lines += [f"── {issue['repo']} ──", issue["title"], "", issue["body"], ""]
    return "\n".join(lines)


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()
    ledger_text = _broadcast.read_ledger(root)
    skills = _resolve_skills(args, root)
    targets = _resolve_targets(args, skills, ledger_text)
    origins = _broadcast.origins_for(skills)
    issues = _build_issues(
        targets, skills, root=root, ledger_text=ledger_text, since=args.since, origins=origins
    )

    if args.apply:
        for issue in issues:
            _broadcast.post_issue(root, issue["repo"], issue["title"], issue["body"])
        result = {"applied": True, "posted": [i["repo"] for i in issues]}
    else:
        result = {"applied": False, "dry_run": True, "issues": issues}

    emit_result(json.dumps(result, indent=2) if args.json else _render_human(result))
    return 0
