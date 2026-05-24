"""``guild overview`` — guildmaster's skills-supplier overview surface.

A deterministic, read-only evidence pack an agent narrates from (issue #12). It
surfaces three things, **skills-scoped only** — it does not reproduce
``steward overview``'s ecosystem relationship graph:

- **Canonical skill set + versions** — every skill guildmaster supplies, its
  origin (guildmaster, or a sibling it only re-broadcasts), and the current
  canonical version (guildmaster's release).
- **Ledger view** — who-consumes-which-skill, read from
  ``docs/skill-sources.md`` (the supplier ledger).
- **Drift signals** — canonical skills no one consumes, per-agent kit gaps, and
  canonical skills the ledger doesn't track yet. These feed ``teach`` /
  ``onboard``.

Read-only: no ``--apply``, no mutation, no network/LLM call. Pre-cutover the
guildmaster ledger is still a consumer-side view with no "Downstream" column, so
the supplier ledger is empty; the verb says so plainly and still reports the
canonical set (see ``docs/cutover.md``).
"""

from __future__ import annotations

import argparse
import json

from guild import __version__
from guild.cli._commands import _broadcast
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import repo_root
from guild.skills import INBOUND_ORIGINS
from guild.skills import ledger as _ledger

LEDGER_PATH = "docs/skill-sources.md"


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "overview",
        help="Skills-supplier overview: canonical set + ledger + drift (read-only).",
        description=(
            "Report guildmaster's canonical skill set + versions, the "
            "upstream/downstream ledger, and drift signals. Skills-scoped and "
            "read-only — no --apply, no mutation. For one agent's full config "
            "(prompt file + culture.yaml + skills), use `guild show <agent>`."
        ),
    )
    parser.add_argument(
        "--scope",
        choices=("all", "self"),
        default="all",
        help="all = whole ledger across the mesh (default); self = one agent's kit + drift.",
    )
    parser.add_argument(
        "agent",
        nargs="?",
        help="Agent name — required with --scope self, ignored with --scope all.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a structured JSON payload to stdout instead of markdown.",
    )
    parser.set_defaults(func=_handle)


def _origin(skill: str) -> str:
    """Origin of a canonical skill: a sibling repo it is re-broadcast from, else
    ``guildmaster`` (guildmaster originates / owns it)."""
    return INBOUND_ORIGINS.get(skill, "guildmaster")


def _bare(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def _build_all(root) -> dict:
    canonical = _broadcast.canonical_skills(root)
    ledger_text = _broadcast.read_ledger(root)
    tracked = _ledger.supplier_skills(ledger_text)
    cmap = _ledger.consumer_map(ledger_text)
    has_supplier_ledger = bool(tracked)

    # Order-preserved union of all consumers across the tracked skills.
    agents: list[str] = []
    for skill in tracked:
        for consumer in cmap.get(skill, []):
            if consumer not in agents:
                agents.append(consumer)

    skills_view = [
        {
            "name": s,
            "origin": _origin(s),
            "version": __version__,
            "consumers": cmap.get(s, []),
        }
        for s in canonical
    ]

    drift = {
        # Canonical skills the supplier ledger does not track at all.
        "unledgered_skills": [s for s in canonical if s not in tracked],
        # Tracked skills with zero consumers (nobody has them yet).
        "uncovered_skills": [s for s in canonical if s in tracked and not cmap.get(s)],
        # Per consumer: canonical skills it does not yet consume.
        "agent_gaps": {
            agent: [s for s in canonical if _bare(agent) not in {_bare(c) for c in cmap.get(s, [])}]
            for agent in agents
        },
    }

    return {
        "scope": "all",
        "version": __version__,
        "ledger_path": LEDGER_PATH,
        "has_supplier_ledger": has_supplier_ledger,
        "canonical_skills": skills_view,
        "agents": agents,
        "drift": drift,
    }


def _build_self(root, agent: str) -> dict:
    canonical = _broadcast.canonical_skills(root)
    ledger_text = _broadcast.read_ledger(root)
    cmap = _ledger.consumer_map(ledger_text)
    tracked = _ledger.supplier_skills(ledger_text)
    has_supplier_ledger = bool(tracked)

    agent_bare = _bare(agent)
    kit = [s for s in canonical if agent_bare in {_bare(c) for c in cmap.get(s, [])}]
    gaps = [s for s in canonical if s not in kit]
    all_consumers_bare = {_bare(c) for s in tracked for c in cmap.get(s, [])}

    return {
        "scope": "self",
        "agent": agent,
        "version": __version__,
        "ledger_path": LEDGER_PATH,
        "has_supplier_ledger": has_supplier_ledger,
        "registered": agent_bare in all_consumers_bare,
        "kit": kit,
        "gaps": gaps,
    }


def _render_all(data: dict) -> str:
    lines = [
        "# guild overview — skills supplier (scope: all)",
        "",
        f"guild {data['version']} · ledger: `{data['ledger_path']}`",
        "",
        f"## Canonical skill set ({len(data['canonical_skills'])})",
        "",
        "| Skill | Origin | Version | Consumers |",
        "|-------|--------|---------|-----------|",
    ]
    for sk in data["canonical_skills"]:
        consumers = ", ".join(sk["consumers"]) if sk["consumers"] else "—"
        lines.append(f"| `{sk['name']}` | {sk['origin']} | {sk['version']} | {consumers} |")
    lines += ["", "## Ledger", ""]
    if not data["has_supplier_ledger"]:
        lines += [
            "No supplier ledger yet — the downstream consumer ledger transfers "
            "from steward at cutover (`docs/cutover.md`). Showing the canonical "
            "set only; drift signals activate post-cutover.",
        ]
    else:
        if data["agents"]:
            lines.append(
                f"Consumers in the ledger ({len(data['agents'])}): "
                + ", ".join(f"`{a}`" for a in data["agents"])
            )
        else:
            lines.append("Supplier ledger present, but no consumers registered yet.")
    lines += ["", "## Drift", ""]
    drift = data["drift"]
    if not data["has_supplier_ledger"]:
        lines.append("_(inactive pre-cutover)_")
    else:
        lines.append(
            "Uncovered skills (no consumer): "
            + (", ".join(f"`{s}`" for s in drift["uncovered_skills"]) or "none")
        )
        lines.append(
            "Unledgered canonical skills: "
            + (", ".join(f"`{s}`" for s in drift["unledgered_skills"]) or "none")
        )
        gapped = {a: g for a, g in drift["agent_gaps"].items() if g}
        if gapped:
            lines.append("Per-agent kit gaps:")
            for agent, gaps in gapped.items():
                lines.append(f"  - `{agent}`: missing " + ", ".join(f"`{s}`" for s in gaps))
        else:
            lines.append("Per-agent kit gaps: none")
    lines += [
        "",
        "_For one agent's full config (prompt file + culture.yaml + skills), "
        "run `guild show <agent>`._",
    ]
    return "\n".join(lines)


def _render_self(data: dict) -> str:
    reg = "registered" if data["registered"] else "NOT registered"
    lines = [
        f"# guild overview — `{data['agent']}` (scope: self)",
        "",
        f"guild {data['version']} · ledger: `{data['ledger_path']}` · {reg}",
        "",
    ]
    if not data["has_supplier_ledger"]:
        lines += [
            "No supplier ledger yet (pre-cutover) — kit + gaps are computed "
            "against an empty consumer ledger; they populate after the "
            "steward → guildmaster cutover (`docs/cutover.md`).",
            "",
        ]
    lines.append(
        "Skill kit (consumed per ledger): " + (", ".join(f"`{s}`" for s in data["kit"]) or "none")
    )
    lines.append(
        "Gaps (canonical skills not yet consumed): "
        + (", ".join(f"`{s}`" for s in data["gaps"]) or "none")
    )
    lines += [
        "",
        f"_For `{data['agent']}`'s full config (prompt file + culture.yaml + "
        "skills), run `guild show <agent>`._",
    ]
    return "\n".join(lines)


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()

    if args.scope == "self":
        if not args.agent:
            raise GuildError(
                code=EXIT_USER_ERROR,
                message="--scope self requires an agent name",
                remediation="pass the agent: `guild overview --scope self <agent>`",
            )
        data = _build_self(root, args.agent)
        rendered = _render_self(data)
    else:
        if args.agent:
            raise GuildError(
                code=EXIT_USER_ERROR,
                message="an agent name is only valid with --scope self",
                remediation="drop the agent, or use `--scope self <agent>`",
            )
        data = _build_all(root)
        rendered = _render_all(data)

    emit_result(json.dumps(data, indent=2) if args.json else rendered)
    return 0
