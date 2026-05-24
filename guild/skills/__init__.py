"""Domain logic for guildmaster's skill-supply verbs (``teach`` / ``onboard``).

Pure, side-effect-light helpers the CLI verbs compose:

- ``ledger`` — read/write the ``docs/skill-sources.md`` consumer ledger.
- ``sources`` — extract a skill's top-level script list + CHANGELOG excerpt.
- ``render`` — compose per-skill sections into one agent-major issue body.
- ``identity`` — render the onboarding identity-setup section.

The CLI (``guild/cli/_commands/``) wires these together; nothing here posts
issues or mutates git — that is the verbs' job, gated by ``--apply``.
"""
