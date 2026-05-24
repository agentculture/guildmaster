"""``guild learn`` — onboard an agent (or human) to this repo.

The broad agent-affordance verb: with no argument it surveys what you can do
here — the CLI verbs and the vendored skills — and points at the runtime
prompt. For depth on a single skill or verb, use ``guild explain <topic>``.
Offline and deterministic: everything is read from the filesystem.
"""

from __future__ import annotations

import argparse
import json

from guild.cli._commands import VERBS
from guild.cli._output import emit_result
from guild.cli._repo import iter_skills, repo_root

_DESC_TRUNCATE = 100


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "learn",
        help="Survey this repo: CLI verbs + vendored skills + the runtime prompt.",
        description=(
            "List the CLI verbs and the skills vendored under .claude/skills/, "
            "and point at the runtime prompt (CLAUDE.md). The onboarding "
            "affordance — run `guild explain <topic>` for depth."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the inventory as a JSON object to stdout instead of prose.",
    )
    parser.set_defaults(func=_handle)


def _truncate(text: str) -> str:
    if len(text) <= _DESC_TRUNCATE:
        return text
    return text[: _DESC_TRUNCATE - 1].rstrip() + "…"


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()
    skills = iter_skills(root)
    has_prompt = (root / "CLAUDE.md").is_file()

    if args.json:
        payload = {
            "version_prompt": "CLAUDE.md" if has_prompt else None,
            "verbs": [{"name": name, "summary": summary} for name, summary in VERBS.items()],
            "skills": [{"name": sk.name, "description": sk.description} for sk in skills],
        }
        emit_result(json.dumps(payload, indent=2))
        return 0

    lines = ["guild — what you can do here", "", "Verbs:"]
    for name, summary in VERBS.items():
        lines.append(f"  guild {name} — {_truncate(summary)}")
    lines.append("")
    if skills:
        lines.append(f"Skills ({len(skills)}):")
        for sk in skills:
            desc = _truncate(sk.description) if sk.description else "(no description)"
            lines.append(f"  {sk.name} — {desc}")
    else:
        lines.append("Skills: (none vendored under .claude/skills/)")
    lines.append("")
    if has_prompt:
        lines.append("Project shape & conventions: see CLAUDE.md")
    lines.append("Run `guild explain <topic>` for a skill's SKILL.md or a verb's detail.")
    emit_result("\n".join(lines))
    return 0
