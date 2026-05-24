---
name: onboard
description: Onboard a brand-new sibling agent into the AgentCulture mesh — guildmaster's new-agent ceremony for supplier operators. Files ONE consolidated issue (full canonical kit as per-skill sections + an identity-setup section), registers the agent in the ledger, and records the pins it should vendor. Dry-run by default; --apply files. Use when an operator says "onboard a new agent/sibling" or "welcome a new repo to the mesh".
type: command
---

# onboard — welcome a brand-new sibling agent

`onboard` is guildmaster's new-agent ceremony, for **supplier operators**
bringing a brand-new **sibling repo** into the mesh. It wraps the
`guild onboard` CLI verb.

It is `teach` of the **whole canonical kit** in new framing, plus the
new-agent bookkeeping:

- one consolidated GitHub issue — every canonical skill as a per-skill section
  (inbound skills, e.g. the devague trio, carry an origin-attribution block) —
  followed by an **identity-setup section** (culture.yaml + backend + prompt
  file, so the sibling passes `steward doctor`);
- **ledger registration** — the agent is added to `docs/skill-sources.md` as a
  downstream consumer of every canonical skill (idempotent);
- a **verification record** — the pins the sibling is expected to vendor.

**Dry-run by default**: it renders the issue, the ledger diff it *would* apply,
and the verification record — writing nothing. `--apply` files the issue, writes
the ledger, and records the pins. Going live is gated on the steward→guildmaster
cutover (`docs/cutover.md`).

## How to run

```bash
# Render the full onboarding ceremony (dry-run):
bash .claude/skills/onboard/scripts/onboard.sh --agent agentculture/newsib

# Commit it — file the issue, write the ledger, record the pins:
bash .claude/skills/onboard/scripts/onboard.sh --agent agentculture/newsib --apply
```

A bare `--agent` name gets the `--org` prefix (default `agentculture`).
`--json` emits a structured payload.
