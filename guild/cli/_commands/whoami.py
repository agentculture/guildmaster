"""``guild whoami`` — report this agent's identity.

The smallest offline probe: it reads ``culture.yaml`` from the enclosing repo
and reports the declared agent suffix(es) + backend alongside the installed
``guild`` version. No network, no shelling out — so it is safe to call in a
loop and deterministic under test.
"""

from __future__ import annotations

import argparse
import json

from guild import __version__
from guild.cli._output import emit_result
from guild.cli._repo import declared_agents, repo_root


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "whoami",
        help="Report this agent's identity (suffix, backend, version).",
        description=(
            "Read the enclosing repo's culture.yaml and report the declared "
            "agent(s) plus the installed guild version. Offline and "
            "side-effect-free — the smallest identity probe."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit identity as a JSON object to stdout instead of human-readable lines.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    root = repo_root()
    agents = declared_agents(root)

    if args.json:
        payload = {
            "version": __version__,
            "repo_root": str(root),
            "agents": [{"suffix": a.get("suffix"), "backend": a.get("backend")} for a in agents],
        }
        emit_result(json.dumps(payload, indent=2))
        return 0

    lines = [f"guild {__version__}", f"repo: {root}"]
    if agents:
        for a in agents:
            lines.append(f"agent: {a.get('suffix', '?')} (backend: {a.get('backend', '?')})")
    else:
        lines.append("agent: (none declared — no culture.yaml)")
    emit_result("\n".join(lines))
    return 0
