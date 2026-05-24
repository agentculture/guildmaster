---
name: teach
description: Teach a set of skills to a set of AgentCulture mesh agents — guildmaster's supplier verb for operators propagating skills to sibling agents. Files one agent-major GitHub issue per target (per-skill sections bundled), new-vs-resync auto-detected from the ledger. Dry-run by default; --apply files. Use when an operator says "teach these skills to those agents", "broadcast a skill update", or "resync vendored skills".
type: command
---

# teach — propagate a set of skills to a set of mesh agents

`teach` is guildmaster's supplier verb. The audience is **supplier operators**
(guildmaster itself; steward during the transition) targeting **sibling repos**
in the mesh. It wraps the `guild teach` CLI verb.

It is **agent-major**: one GitHub issue per target agent, bundling a per-skill
*section* for every skill that agent receives — not one issue per skill.
New-vs-resync framing is auto-detected per `(skill, agent)` from
`docs/skill-sources.md`. **Dry-run by default**; pass `--apply` to file the
issues. Going live is gated on the steward→guildmaster cutover (`docs/cutover.md`).

## How to run

```bash
# Render (dry-run) — what would be filed, nothing posted:
bash .claude/skills/teach/scripts/teach.sh --skill cicd --skill communicate --to tipalti

# Teach the full canonical kit to two agents and file the issues:
bash .claude/skills/teach/scripts/teach.sh --all --to daria --to tipalti --apply
```

Skills must be selected explicitly (`--skill`, repeatable, or `--all`) — there
is no implicit default. Targets come from `--to` (bare names get `--org`,
default `agentculture`), falling back to the ledger's current consumers per
skill when `--to` is omitted. `--json` emits a structured payload.
