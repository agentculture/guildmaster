"""guild subcommands.

``VERBS`` is the canonical one-line summary of each agent-affordance verb,
shared by ``learn`` (which lists them) and ``explain`` (which can detail one).
Keep it in sync with the registered subcommands.
"""

VERBS: dict[str, str] = {
    "whoami": (
        "Report this agent's identity — suffix, backend, and version. "
        "The smallest offline auth/identity probe."
    ),
    "learn": (
        "Onboard here: list the CLI verbs and vendored skills, and point "
        "at the runtime prompt (CLAUDE.md)."
    ),
    "explain": (
        "Explain one topic in depth — a vendored skill (prints its SKILL.md) " "or a CLI verb."
    ),
    "teach": (
        "Propagate a set of skills to a set of mesh agents — one agent-major "
        "issue per target. Dry-run by default; --apply files."
    ),
    "onboard": (
        "Onboard a new sibling: the full canonical kit + identity-setup section "
        "+ ledger registration + verification record. Dry-run by default."
    ),
}

__all__ = ["VERBS"]
