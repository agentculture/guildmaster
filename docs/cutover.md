# Broadcaster cutover — steward → guildmaster

guildmaster's `teach` / `onboard` verbs are the mesh's skill-broadcast surface
(see the README "Supplier verbs" section and
[issue #1 §1](https://github.com/agentculture/guildmaster/issues/1)). Standing
them up does **not** make guildmaster the live broadcaster the moment the code
merges. There is a hard precondition.

## Status: complete (2026-05-24)

The steward → guildmaster broadcaster cutover is **done**. guildmaster owns the
supplier ledger (`docs/skill-sources.md`, migrated to supplier shape in
[#16](https://github.com/agentculture/guildmaster/pull/16)), and the operator
confirmed steward has stopped firing `announce-skill-update` and accepts
`teach` / `onboard` as the broadcast role. guildmaster is now the **sole
broadcaster**; `--apply` is **live**. First post-cutover broadcast: the
2026-05-24 `guild teach` resync to 7 agents (katvan, antoine, appsec, culture,
auntiepypi, agex-cli, devague).

> **Records reconciliation (steward side).** steward's [PR #62](https://github.com/agentculture/steward/pull/62)
> recorded only a *partial* handoff (devague-trio downstream tracking) and its
> ledger/[#10](https://github.com/agentculture/guildmaster/issues/10) prose still
> describe steward as the live broadcaster "until `guild announce-skill-update`
> ships". That verb is intentionally **not** shipping — `teach` / `onboard`
> supersede it. The operational handover is confirmed; steward's written records
> are to be reconciled to match (steward's lane / #10).

## Precondition (historical — now satisfied)

> **`teach` / `onboard` must not broadcast in production (`--apply`) until
> `steward` has confirmed it stopped broadcasting.** Running both broadcasters
> at once would mean **two live broadcasters** and double-posted briefs — exactly
> what [issue #10](https://github.com/agentculture/guildmaster/issues/10) forbids.

This precondition is **satisfied** as of 2026-05-24. `--dry-run` (the default)
remains the safe rendering mode; `--apply` is now sanctioned.

## The cutover, step by step

1. **[done]** guildmaster's `teach` / `onboard` are green and reviewed.
2. **[done]** guildmaster migrated `docs/skill-sources.md` to the supplier shape
   and took ownership of the ledger + broadcast role + skill-version tracking
   ([#16](https://github.com/agentculture/guildmaster/pull/16)).
3. **[done]** guildmaster pinged `steward` that the broadcast surface is ready
   ([steward#61](https://github.com/agentculture/steward/issues/61)).
4. **[done]** steward stopped broadcasting and the operator confirmed the
   handover (records reconciliation pending on steward's side — see note above).
5. **[done]** guildmaster is the sole broadcaster; `--apply` is live.

## Why no separate `announce-skill-update` verb

Issue #10 asked guildmaster to stand up its own `announce-skill-update`
subcommand (steward's skill-major, one-skill-→-N-consumers verb). guildmaster
fulfills the same broadcast **role** through `teach` / `onboard` instead — which
are **agent-major** (one issue per agent, bundling per-skill sections). `teach`
with one skill to one agent covers the single-skill case, so a separate verb
would be redundant. The reconciliation is tracked on issue #10; see
`docs/specs/` and `docs/plans/` for the converged design.
