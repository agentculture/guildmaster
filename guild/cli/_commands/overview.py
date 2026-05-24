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

``--scope mesh`` is the live alternative to the ledger: instead of reading
``docs/skill-sources.md``, it surveys every agent in the workspace
(``<workspace>/*/culture.yaml``) straight off the filesystem and reports, per
agent, which canonical skills are present / **stale** (the agent's copy differs
from guildmaster's canonical copy by content fingerprint) / **missing**. This
answers "what's missing or stale, and where" without waiting for the cutover —
still skills-scoped, still no dependency/relationship graph.

Read-only: no ``--apply``, no mutation, no network/LLM call. Pre-cutover the
guildmaster ledger is still a consumer-side view with no "Downstream" column, so
the supplier ledger is empty; ``--scope all``/``self`` say so plainly and still
report the canonical set (see ``docs/cutover.md``), while ``--scope mesh`` does
not depend on the ledger at all.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from guild import __version__
from guild.cli._commands import _broadcast
from guild.cli._errors import EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import discover_agents, iter_skills, repo_root, skill_fingerprint
from guild.skills import INBOUND_ORIGINS, SELF_SKILLS
from guild.skills import ledger as _ledger

LEDGER_PATH = "docs/skill-sources.md"


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "overview",
        help="Skills-supplier overview: canonical set + ledger + drift, or a live mesh survey.",
        description=(
            "Report guildmaster's canonical skill set + versions, the "
            "upstream/downstream ledger, and drift signals (--scope all/self, "
            "from the ledger); or survey every agent's vendored skills live from "
            "the filesystem and flag what's missing or stale per agent (--scope "
            "mesh). Skills-scoped and read-only — no --apply, no mutation, no "
            "dependency/relationship graph (that is steward's lane). For one "
            "agent's full config, use `guild show <agent>`."
        ),
    )
    parser.add_argument(
        "--scope",
        choices=("all", "self", "mesh"),
        default="all",
        help=(
            "all = whole ledger across the mesh (default); self = one agent's "
            "kit + drift (from the ledger); mesh = live filesystem survey of "
            "every agent's skills + missing/stale signals."
        ),
    )
    parser.add_argument(
        "agent",
        nargs="?",
        help="Agent name — required with --scope self; ignored with --scope all/mesh.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Workspace dir to survey for --scope mesh (default: the parent of this repo).",
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


def _build_mesh(root, workspace_root) -> dict:
    """Live filesystem survey of every agent's vendored skills + drift.

    Canonical reference is guildmaster's own supplied set (its ``.claude/skills``
    minus ``SELF_SKILLS``); an agent's copy is **stale** when its content
    fingerprint differs from guildmaster's, **missing** when absent. Inventory
    only — no dependency/relationship graph (that judgment is steward's lane).
    """
    canonical = [s for s in iter_skills(root) if s.name not in SELF_SKILLS]
    canonical_fp = {s.name: skill_fingerprint(s.path) for s in canonical}
    canonical_names = [s.name for s in canonical]

    agents_view: list[dict] = []
    for agent in discover_agents(workspace_root):
        by_name = {s.name: s for s in iter_skills(agent.repo_path)}
        per_skill: list[dict] = []
        missing: list[str] = []
        stale: list[str] = []
        for name in canonical_names:
            skill = by_name.get(name)
            if skill is None:
                missing.append(name)
                per_skill.append({"skill": name, "status": "missing", "fingerprint": ""})
                continue
            fingerprint = skill_fingerprint(skill.path)
            status = "current" if fingerprint == canonical_fp[name] else "stale"
            if status == "stale":
                stale.append(name)
            per_skill.append({"skill": name, "status": status, "fingerprint": fingerprint})
        agents_view.append(
            {
                "suffix": agent.suffix,
                "backend": agent.backend,
                "repo": agent.repo_name,
                "skills": sorted(by_name),
                "missing": missing,
                "stale": stale,
                "extra": sorted(n for n in by_name if n not in canonical_fp),
                "per_skill": per_skill,
            }
        )

    return {
        "scope": "mesh",
        "version": __version__,
        "workspace_root": str(workspace_root),
        "canonical_skills": [{"name": n, "fingerprint": canonical_fp[n]} for n in canonical_names],
        "agents": agents_view,
    }


def _names_or(names, empty: str = "none") -> str:
    """Backtick-join *names*, or *empty* when there are none."""
    return ", ".join(f"`{n}`" for n in names) or empty


def _render_canonical_table(skills: list[dict]) -> list[str]:
    lines = [
        f"## Canonical skill set ({len(skills)})",
        "",
        "| Skill | Origin | Version | Consumers |",
        "|-------|--------|---------|-----------|",
    ]
    for sk in skills:
        consumers = ", ".join(sk["consumers"]) if sk["consumers"] else "—"
        lines.append(f"| `{sk['name']}` | {sk['origin']} | {sk['version']} | {consumers} |")
    return lines


def _render_ledger_section(data: dict) -> list[str]:
    lines = ["## Ledger", ""]
    if not data["has_supplier_ledger"]:
        lines.append(
            "No supplier ledger yet — the downstream consumer ledger transfers "
            "from steward at cutover (`docs/cutover.md`). Showing the canonical "
            "set only; drift signals activate post-cutover."
        )
    elif data["agents"]:
        lines.append(
            f"Consumers in the ledger ({len(data['agents'])}): " + _names_or(data["agents"])
        )
    else:
        lines.append("Supplier ledger present, but no consumers registered yet.")
    return lines


def _render_drift_section(data: dict) -> list[str]:
    lines = ["## Drift", ""]
    if not data["has_supplier_ledger"]:
        lines.append("_(inactive pre-cutover)_")
        return lines
    drift = data["drift"]
    lines.append("Uncovered skills (no consumer): " + _names_or(drift["uncovered_skills"]))
    lines.append("Unledgered canonical skills: " + _names_or(drift["unledgered_skills"]))
    gapped = {a: g for a, g in drift["agent_gaps"].items() if g}
    if not gapped:
        lines.append("Per-agent kit gaps: none")
        return lines
    lines.append("Per-agent kit gaps:")
    for agent, gaps in gapped.items():
        lines.append(f"  - `{agent}`: missing " + _names_or(gaps))
    return lines


def _render_all(data: dict) -> str:
    lines = [
        "# guild overview — skills supplier (scope: all)",
        "",
        f"guild {data['version']} · ledger: `{data['ledger_path']}`",
        "",
        *_render_canonical_table(data["canonical_skills"]),
        "",
        *_render_ledger_section(data),
        "",
        *_render_drift_section(data),
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


def _count_or_dash(names) -> str:
    """The count of *names*, or an em dash when there are none."""
    return str(len(names)) if names else "—"


def _render_mesh(data: dict) -> str:
    agents = data["agents"]
    canonical = data["canonical_skills"]
    lines = [
        "# guild overview — mesh skill inventory (scope: mesh)",
        "",
        f"guild {data['version']} · workspace: `{data['workspace_root']}` · "
        f"{len(agents)} agent(s) · canonical set: {len(canonical)} skill(s)",
        "",
    ]
    if not agents:
        lines += [
            "No agents found — no `*/culture.yaml` under the workspace root. Pass "
            "`--workspace-root DIR` to point at the directory holding the sibling repos.",
        ]
        return "\n".join(lines)

    lines += [
        "## Agents",
        "",
        "| Agent | Backend | Repo | Skills | Missing | Stale |",
        "|-------|---------|------|--------|---------|-------|",
    ]
    for a in agents:
        lines.append(
            f"| `{a['suffix']}` | {a['backend'] or '—'} | `{a['repo']}` | "
            f"{len(a['skills'])} | {_count_or_dash(a['missing'])} | "
            f"{_count_or_dash(a['stale'])} |"
        )

    drifting = [a for a in agents if a["missing"] or a["stale"]]
    lines += ["", "## Missing & stale detail", ""]
    if not drifting:
        lines.append("Every agent's vendored copies match guildmaster's canonical set.")
    else:
        for a in drifting:
            parts = []
            if a["stale"]:
                parts.append("stale " + _names_or(a["stale"]))
            if a["missing"]:
                parts.append("missing " + _names_or(a["missing"]))
            lines.append(f"- `{a['suffix']}` (`{a['repo']}`): " + "; ".join(parts))

    lines += [
        "",
        "_Canonical = guildmaster's supplied set (its skills minus its own operator "
        "verbs). \"Stale\" = the agent's copy differs from guildmaster's by content "
        'fingerprint; "missing" = the agent lacks a canonical skill. Inventory only — '
        "the dependency/relationship graph is steward's lane._",
    ]
    return "\n".join(lines)


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()

    if args.scope != "self" and args.agent:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message="an agent name is only valid with --scope self",
            remediation="drop the agent, or use `--scope self <agent>`",
        )

    if args.scope == "self":
        if not args.agent:
            raise GuildError(
                code=EXIT_USER_ERROR,
                message="--scope self requires an agent name",
                remediation="pass the agent: `guild overview --scope self <agent>`",
            )
        data = _build_self(root, args.agent)
        rendered = _render_self(data)
    elif args.scope == "mesh":
        workspace_root = (args.workspace_root or root.parent).expanduser().resolve()
        data = _build_mesh(root, workspace_root)
        rendered = _render_mesh(data)
    else:  # all
        data = _build_all(root)
        rendered = _render_all(data)

    emit_result(json.dumps(data, indent=2) if args.json else rendered)
    return 0
