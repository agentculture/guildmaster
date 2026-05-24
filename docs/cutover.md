# Broadcaster cutover — steward → guildmaster

guildmaster's `teach` / `onboard` verbs are the mesh's skill-broadcast surface
(see the README "Supplier verbs" section and
[issue #1 §1](https://github.com/agentculture/guildmaster/issues/1)). Standing
them up does **not** make guildmaster the live broadcaster the moment the code
merges. There is a hard precondition.

## Precondition (load-bearing)

> **`teach` / `onboard` must not broadcast in production (`--apply`) until the
> staged steward → guildmaster cutover has happened.** Until then, `steward`
> holds the live ledger and fires drift broadcasts. Running guildmaster's
> verbs with `--apply` before cutover would mean **two live broadcasters** and
> double-posted briefs — exactly what
> [issue #10](https://github.com/agentculture/guildmaster/issues/10) forbids.

`--dry-run` (the default) is always safe: it renders briefs and ledger /
verification diffs without posting. Only `--apply` is gated.

## The cutover, in one step

When guildmaster's `teach` / `onboard` are green and reviewed:

1. guildmaster pings `steward` that the broadcast surface is ready.
2. In a single coordinated step: **steward stops broadcasting** and hands over
   the canonical `docs/skill-sources.md` ledger; **guildmaster takes ownership**
   of the ledger + the broadcast role + skill-version tracking.
3. From then on, guildmaster is the sole broadcaster. No overlap, no two
   competing ledgers.

Until step 2 completes, treat any guildmaster `--apply` broadcast as **off** —
operate in dry-run only.

## Why no separate `announce-skill-update` verb

Issue #10 asked guildmaster to stand up its own `announce-skill-update`
subcommand (steward's skill-major, one-skill-→-N-consumers verb). guildmaster
fulfills the same broadcast **role** through `teach` / `onboard` instead — which
are **agent-major** (one issue per agent, bundling per-skill sections). `teach`
with one skill to one agent covers the single-skill case, so a separate verb
would be redundant. The reconciliation is tracked on issue #10; see
`docs/specs/` and `docs/plans/` for the converged design.
