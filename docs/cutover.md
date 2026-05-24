# Broadcaster cutover — steward → guildmaster

guildmaster's `teach` / `onboard` verbs are the mesh's skill-broadcast surface
(see the README "Supplier verbs" section and
[issue #1 §1](https://github.com/agentculture/guildmaster/issues/1)). Standing
them up does **not** make guildmaster the live broadcaster the moment the code
merges. There is a hard precondition.

## Status: in progress — awaiting steward's ack (2026-05-24)

guildmaster's side of the cutover has landed: `teach` / `onboard` are green and
reviewed, and `docs/skill-sources.md` has been migrated to the **supplier
shape** (canonical set + Downstream column carried over from steward's ledger).
The handshake ping (step 1 below) has been sent. The **one remaining gate** is
steward's ack that it has stopped broadcasting (step 2). Until that ack lands,
`--apply` stays **off** — operate in dry-run only.

## Precondition (load-bearing)

> **`teach` / `onboard` must not broadcast in production (`--apply`) until
> `steward` has confirmed it stopped broadcasting.** While both sides could
> broadcast, running guildmaster's verbs with `--apply` would mean **two live
> broadcasters** and double-posted briefs — exactly what
> [issue #10](https://github.com/agentculture/guildmaster/issues/10) forbids.

`--dry-run` (the default) is always safe: it renders briefs and ledger /
verification diffs without posting. Only `--apply` is gated.

## The cutover, step by step

1. **[done]** guildmaster's `teach` / `onboard` are green and reviewed.
2. **[done]** guildmaster migrates `docs/skill-sources.md` to the supplier shape
   and takes ownership of the ledger + broadcast role + skill-version tracking
   (this PR).
3. **[done]** guildmaster pings `steward` that the broadcast surface is ready.
4. **[pending — steward]** steward **stops broadcasting**, retires its
   supplier-ledger ownership, and acks the handover.
5. **[pending]** From then on, guildmaster is the sole broadcaster. No overlap,
   no two competing ledgers — and `--apply` goes live.

Until step 4's ack lands, treat any guildmaster `--apply` broadcast as **off** —
operate in dry-run only.

## Why no separate `announce-skill-update` verb

Issue #10 asked guildmaster to stand up its own `announce-skill-update`
subcommand (steward's skill-major, one-skill-→-N-consumers verb). guildmaster
fulfills the same broadcast **role** through `teach` / `onboard` instead — which
are **agent-major** (one issue per agent, bundling per-skill sections). `teach`
with one skill to one agent covers the single-skill case, so a separate verb
would be redundant. The reconciliation is tracked on issue #10; see
`docs/specs/` and `docs/plans/` for the converged design.
