"""Domain logic for guildmaster's skill-supply verbs (``teach`` / ``onboard``).

Pure, side-effect-light helpers the CLI verbs compose:

- ``ledger`` — read/write the ``docs/skill-sources.md`` consumer ledger.
- ``sources`` — extract a skill's top-level script list + CHANGELOG excerpt.
- ``render`` — compose per-skill sections into one agent-major issue body.
- ``identity`` — render the onboarding identity-setup section.

The CLI (``guild/cli/_commands/``) wires these together; nothing here posts
issues or mutates git — that is the verbs' job, gated by ``--apply``.
"""

from __future__ import annotations

# Skills whose origin is a *sibling* (not guildmaster): re-broadcasting them
# carries an origin-attribution block so consumers know guildmaster only
# re-broadcasts. Mirrors the "Inbound workflow skills" + "Inbound first-party"
# sections of ``docs/skill-sources.md`` (the devague trio; convertible's
# ``outsource``).
INBOUND_ORIGINS: dict[str, str] = {
    "think": "agentculture/devague",
    "spec-to-plan": "agentculture/devague",
    "assign-to-workforce": "agentculture/devague",
    "outsource": "agentculture/convertible",
}

# guildmaster's own skills — present in ``.claude/skills/`` but NOT part of the
# canonical kit guildmaster supplies to siblings: the operator verbs (``teach`` /
# ``onboard``) and ``guild``, the affordance skill wrapping guildmaster's own
# ``guild`` CLI surfaces (e.g. ``guild overview``), which is meaningless on a
# sibling that doesn't ship the ``guild`` binary.
SELF_SKILLS: frozenset[str] = frozenset({"teach", "onboard", "guild"})
