---
name: guild
description: >
  Run guildmaster's skills-supplier overview and narrate it. Run `guild
  overview` (via scripts/overview.sh) for the deterministic evidence pack — the
  canonical skill set + versions/origins, the docs/skill-sources.md ledger, and
  skills-scoped drift signals — then narrate three separated layers: observed
  facts, inferred relationships, and suggestions (each naming the command that
  enacts it). Use when an operator asks "what skills do we supply", "who
  consumes what", "is anything drifting", or "what should I teach next".
  Skills-scoped and reflect-only — it surfaces and interprets supplier-side
  skill/version signals; it does NOT narrate the agent relationship graph or
  judge alignment (that stays with steward's org-overview / steward doctor).
  The skills-scoped excerpt of steward's `org-overview` narration contract
  (cite-don't-import, issue #12).
type: command
---

# guild — narrate guildmaster's own supplier surfaces

guildmaster is the mesh's skills **supplier**, and it owns the *inventory*
surfaces ([issue #12](https://github.com/agentculture/guildmaster/issues/12)).
The per-agent half (`guild show`) is backed by the vendored `agent-config`
skill. **This skill is the supplier half: the affordance for `guild overview`.**
It houses the scripts that run guildmaster's own read-only CLI surfaces and the
contract for narrating them — `overview` is the one script today.

Unlike the vendored skills, this one is **guildmaster's own** (origin =
`guildmaster`, not cited from steward): `guild overview` is a pure-Python,
read-only CLI verb, and `scripts/overview.sh` is the thin deterministic wrapper
that invokes it. The script picks how to call `guild` (installed console
script → `uv run` → `python -m guild`) and delegates; it interprets nothing.

**The load-bearing split** (this is the skills-scoped excerpt of steward's
`org-overview` narration contract — issue #12, cite-don't-import):

- **The CLI (`guild overview`) emits only deterministic facts** — the canonical
  skill set, the ledger view, and neutral drift signals. No LLM, no
  interpretation, mutates nothing.
- **This skill is where the agent interprets** — turning those facts into
  inferred relationships and suggestions. **Never present an inference as a
  fact**, and keep the layers in separate sections.

## What `overview` answers

A skills-scoped evidence pack — **not** `steward overview`'s ecosystem
relationship graph (issue #12: inventory → guildmaster; judgment → steward):

1. **Canonical skill set + versions** — every skill guildmaster supplies, its
   origin (`guildmaster`, or a sibling it only re-broadcasts), and the current
   canonical version, plus per-skill consumers.
2. **Ledger view** — who-consumes-which-skill, read from `docs/skill-sources.md`.
3. **Drift signals** — canonical skills no one consumes, canonical skills the
   ledger doesn't track yet, and per-agent kit gaps. These feed `teach` /
   `onboard`.

**Pre-cutover** the guildmaster ledger is still a consumer-side view with no
"Downstream" column, so the supplier ledger is empty and drift is inactive; the
verb reports the canonical set and says so plainly (see `docs/cutover.md`).

## When to use

- An operator asks "what skills do we supply" / "what's the canonical set".
- "Who has skill `<x>`?" / "who consumes what?" / "is anything drifting?"
- "What should I `teach` next?" — overview's gaps are the input to `teach`.
- Before `guild teach` / `guild onboard`, to see uncovered skills and kit gaps.

## How to run

One script. Pick the scope (or just run `guild overview`, which this wraps):

```bash
# Whole mesh — the canonical set + ledger + drift across all agents (default)
.claude/skills/guild/scripts/overview.sh

# One agent — that agent's kit + gaps (first positional → --scope self)
.claude/skills/guild/scripts/overview.sh daria

# Machine-readable evidence for precise reasoning
.claude/skills/guild/scripts/overview.sh --json
.claude/skills/guild/scripts/overview.sh daria --json
```

The script prints the CLI's markdown by default: the canonical-skill table, a
ledger section, and a drift section. The exact per-skill consumer and gap lists
live in `--json`.

## Narrate three layers — never blur them

`guild overview` emits only deterministic facts; this skill is where you
interpret them. Keep the three layers in separate sections, and never present
an inference as a fact:

1. **Observed facts.** Summarize the canonical set + versions/origins and the
   ledger view in your own words — lead with what the counts reveal (the
   canonical set, who's behind, who's unregistered). State only what the CLI
   reported; don't reproduce the raw signal lists verbatim (read `--json` only
   when you need an exact list to act on). Pre-cutover, say so plainly: the
   ledger has no downstream column yet, so consumers are empty and drift is
   inactive.
2. **Inferred relationships** (mark clearly as inferred). Connect facts no
   single ledger row states outright — e.g. two consumers vendored from the
   same upstream skill *both* lag a canonical bump (a shared exposure), or a
   skill only `guildmaster` carries is a single point of supply.
3. **Suggestions** (kept separate from facts, and *named, not run*). Seed these
   from the skills-scoped drift signals — for each, name the concrete next step
   and the command that enacts it, then stop.

### Signal → suggestion (skills-scoped only)

These are the **skill/version** signals `guild overview` emits — guildmaster's
supplier lane:

| Drift signal (from `guild overview`) | Reading | Named follow-up — name it, do NOT auto-run |
|--------------------------------------|---------|--------------------------------------------|
| `unledgered_skills` | a canonical skill the ledger doesn't track (no owner row) | Fix the ledger: add it to `docs/skill-sources.md` |
| `uncovered_skills` | a canonical skill no agent consumes (orphan) | Confirm intentional, then `teach` it, or retire it |
| `agent_gaps` (per-agent missing skill) | a consumer behind / missing a skill | `guild teach --skill <name> --to <agent>` to close the gap |
| agent not registered in the ledger | a sibling not yet onboarded | `guild onboard --agent <owner/repo>` |
| consumer behind the canonical pin (post-cutover) | a team on an outdated procedure | Re-vendor: `guild teach` / `onboard` to the current pin |

### Out of scope — steward's lane

The **relationship** signals — `overlap`, `over-connected-agent`,
`isolated-repo` — and the typed agent relationship graph are **not** narrated
here. Those belong to steward's `org-overview` / `steward overview`. guildmaster
narrates skills/version drift, not the ecosystem graph or alignment judgment.

### Reflect-only

This skill **sees, reflects, and suggests — it does not act.** For every
suggestion, name the concrete next step and the command that enacts it, then
stop. Editing the ledger, filing an issue, or running `teach` / `onboard` is a
separate, explicit step the operator chooses. The skill writes nothing to disk
and mutates no repo — output is the chat conversation only. Read-only: no
`--apply`, no mutation, no network/LLM call.
