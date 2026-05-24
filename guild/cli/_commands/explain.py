"""``guild explain <topic>`` — explain one skill or verb in depth.

The narrow agent-affordance verb (``learn`` is the broad survey). If the topic
names a vendored skill, its full ``SKILL.md`` is printed; if it names a CLI
verb, the verb's one-line summary is printed; otherwise the command fails with
the list of valid topics. Offline and deterministic.
"""

from __future__ import annotations

import argparse
import json

from guild.cli._commands import VERBS
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import iter_skills, repo_root


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "explain",
        help="Explain one topic in depth — a vendored skill or a CLI verb.",
        description=(
            "Print the full SKILL.md for a vendored skill, or the summary for "
            "a CLI verb. Run `guild learn` to see the available topics."
        ),
    )
    parser.add_argument(
        "topic",
        help="A vendored skill name (under .claude/skills/) or a CLI verb.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Wrap the explanation in a JSON object on stdout.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    topic = args.topic
    root = repo_root()

    # Index skills by both frontmatter name and directory name so `explain`
    # works even if a skill's frontmatter name drifts from its directory.
    skills = {}
    for sk in iter_skills(root):
        skills.setdefault(sk.name, sk)
        skills.setdefault(sk.path.name, sk)

    if topic in skills:
        sk = skills[topic]
        content = sk.skill_md.read_text(encoding="utf-8")
        if args.json:
            emit_result(
                json.dumps(
                    {
                        "kind": "skill",
                        "name": sk.name,
                        "path": str(sk.skill_md),
                        "content": content,
                    },
                    indent=2,
                )
            )
        else:
            emit_result(content)
        return 0

    if topic in VERBS:
        if args.json:
            emit_result(
                json.dumps({"kind": "verb", "name": topic, "summary": VERBS[topic]}, indent=2)
            )
        else:
            emit_result(f"guild {topic} — {VERBS[topic]}")
        return 0

    valid = sorted(set(VERBS) | set(skills))
    raise GuildError(
        code=EXIT_USER_ERROR,
        message=f"unknown topic '{topic}'",
        remediation="valid topics: " + ", ".join(valid),
    )
