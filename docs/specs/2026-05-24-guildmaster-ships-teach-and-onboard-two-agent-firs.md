# guildmaster ships /teach and /onboard: two agent-first verbs layered over its announce-skill-update broadcast. 'guild teach' pushes a chosen SET of skills to a chosen SET of mesh agents in one command; 'guild onboard' welcomes a brand-new sibling agent with the full canonical skill kit, an identity-setup brief, ledger registration, and post-onboard verification. Both default to dry-run; --apply files the issues.

> guildmaster ships /teach and /onboard: two agent-first verbs layered over its announce-skill-update broadcast. 'guild teach' pushes a chosen SET of skills to a chosen SET of mesh agents in one command; 'guild onboard' welcomes a brand-new sibling agent with the full canonical skill kit, an identity-setup brief, ledger registration, and post-onboard verification. Both default to dry-run; --apply files the issues.

## Audience

- AgentCulture mesh operators and resident supplier agents (guildmaster itself; steward during transition). Each verb's TARGET is a sibling repo/agent: an existing consumer (teach=resync) or a brand-new sibling (onboard).

## Before → After

- Before: Guildmaster has NO broadcast capability of its own yet; steward holds the live broadcaster. Teaching a SET of skills or standing up a NEW agent is fully manual: hand-rendered briefs, hand-edited ledger, ad-hoc onboarding (e.g. issue #1), no verification step.
- After: An operator runs ONE command to propagate N skills to M agents (teach) or to fully onboard a new sibling (onboard) — instead of hand-running announce-skill-update once per skill, hand-editing the ledger, and hand-writing a welcome brief.

## Why it matters

- guildmaster's charter (issue #1 §1) is skills supplier/manager. 'Supply a set of skills' and 'onboard a new consumer' are its two headline verbs; they must be one-shot, safe-by-default, and leave the ledger correct — or the supplier role isn't real.

## Requirements

- onboard --apply registers the new agent in the downstream column of every canonical skill row in docs/skill-sources.md, idempotently (a second run is a no-op).
  - honesty: after onboard --apply, docs/skill-sources.md lists the new agent in the downstream column of every canonical skill row; a second run changes zero bytes (idempotent, no duplicate entries).
- For each (skill, agent) pair, new-vs-resync framing is auto-detected from the ledger: existing consumer -> resync brief, new -> new brief; teach/onboard never post a 'new' brief to an existing consumer.
  - honesty: for each (skill, agent): if the agent already appears in that skill's ledger downstream -> resync framing, else -> new framing; never a 'new' brief to an existing consumer, never a 'resync' to a stranger.
- onboard's brief includes an identity-setup section so a new sibling can pass steward doctor's prompt-file-present + backend-consistency invariants.
  - honesty: a sibling that follows the onboard brief's identity section ends up with a culture.yaml + matching prompt file that 'steward doctor --scope self' accepts (prompt-file-present + backend-consistency pass).
- With no --apply, neither verb posts an issue or mutates the ledger/verification state; both print exactly what they WOULD do and exit 0.
  - honesty: with no --apply, an issue/filesystem diff shows zero changes — no issue created, no ledger byte mutated — and exit code is 0.
- teach renders ONE agent-major issue per target agent: for each agent, compose a per-skill section (script-list + CHANGELOG excerpt + cite locations — lifting steward's announce templates as per-skill SECTIONS) for every taught skill into a single issue, posted via agtag. Targeting from --to, falling back to the ledger per skill.
  - honesty: teaching skills [A,B] to agents [X,Y] files exactly TWO issues — one to X, one to Y — each bundling an A-section AND a B-section; never one issue per skill, never a separate per-skill broadcast call.
- onboard reuses teach's rendering for the FULL canonical set in NEW framing, attributing the inbound trio (think/spec-to-plan/assign-to-workforce) to agentculture/devague as origin with guildmaster as re-broadcaster.
  - honesty: an onboarded sibling sees the devague trio (think/spec-to-plan/assign-to-workforce) attributed to agentculture/devague (origin block present) with guildmaster as re-broadcaster, rendered as sections within the single onboarding issue.

## Honesty conditions

- onboard X == teach <all-canonical> to X in NEW framing + ledger registration + verification record. teach is the single rendering+posting engine; onboard adds only kit-selection + bookkeeping. No separate broadcast path (no announce-skill-update verb) exists.
- Any real user of these verbs is always a supplier-agent operator running guildmaster, targeting a sibling repo that is either an existing ledger consumer (teach) or a brand-new sibling (onboard) — no other actor type needs teach/onboard.
- The full propagation (N skills x M agents) or onboarding ceremony completes from a SINGLE command invocation — no manual per-skill or per-agent follow-up step remains afterward.
- Without one-shot teach + onboard, guildmaster cannot credibly own the supplier role: the ledger drifts or onboarding stays manual. The two verbs are necessary, not nice-to-have, for the #1 §1 charter.
- teach/onboard going live is GATED on the steward->guildmaster cutover; running them while steward still broadcasts would double-post, so neither the verbs nor the operator broadcast competitively before cutover.
- Today guildmaster has no broadcast verb of its own and no command performs set-level teaching or onboarding — the work is provably manual (demonstrable by the absence of such a verb in the CLI).
- The teach dry-run for two skills to one agent emits exactly ONE issue body containing two correctly-rendered per-skill sections — verifiable by inspecting the rendered markdown without posting anything.
- The onboard dry-run emits exactly ONE issue body (all canonical sections + identity section) PLUS a shown-but-unapplied ledger diff and a verification record — all artifacts present in output, none posted or written.

## Success signals

- 'guild teach --skill cicd --skill communicate --to tipalti' (dry-run) renders ONE issue to tipalti containing BOTH a cicd section and a communicate section (each with correct script-list + CHANGELOG excerpt); --apply files that single issue; non-zero exit on any post failure.
- 'guild onboard --agent agentculture/newsib' (dry-run) renders ONE consolidated onboarding issue: every canonical skill as a section (devague trio attributed to agentculture/devague) + an identity-setup section + the ledger diff that WOULD register newsib + the verification record; --apply files the one issue, writes the ledger, records pins.

## Scope / boundaries

- Runs only AFTER the staged steward->guildmaster broadcaster cutover (#10) — not a second live broadcaster; no two competing ledgers mid-migration.

## Non-goals

- NOT inbound vendoring — onboard pushes issues to the new sibling; it never edits the target repo's files or copies skills into a local checkout.
- NOT remote identity creation — 'identity scaffold' is a setup SECTION IN THE BRIEF the new sibling follows; guildmaster never writes their culture.yaml/prompt files.

## Decisions

- Direction = OUTBOUND/push: teach and onboard file GitHub issues on target agents' repos via announce-skill-update; they never vendor skills into a local checkout.
- Onboard scope = ledger + identity + verify: beyond firing the kit, onboard (a) registers the new agent in docs/skill-sources.md, (b) includes an identity-setup section in the brief (culture.yaml + backend + prompt file), (c) records post-onboard verification state.
- Safe-by-default: both verbs default to dry-run (render briefs + show ledger/verification diffs); --apply files issues and writes the ledger (CLAUDE.md agent-first rule).
- teach/onboard SUPERSEDE announce-skill-update: guildmaster ships NO separate verb by that name. teach (one skill -> one agent) covers the #10 broadcast case; teach/onboard own the rendering+posting+ledger machinery internally. The #10 broadcast ROLE is fulfilled — reconcile its literal acceptance criteria with steward via a reply on #10.
- Issue granularity = AGENT-MAJOR: one issue per target agent, bundling all relevant skills as per-skill sections (teach: every taught skill; onboard: all canonical + an identity-setup section). NOT one issue per skill. (Resolves parked v2.)
- teach skill-selection has NO implicit default: skills are explicit via --skill (repeatable) and --all (= canonical set, explicit). Bare invocation with no skills selected -> error. Hidden defaults create unexpected results. (Resolves parked v3.)

## Hard questions

- risk: If teach/onboard duplicate announce's posting/templating instead of composing it, the supplier ends up with two divergent broadcasters — exactly what #10's staged cutover forbids.

## Open / follow-up

- Build-order dependency: announce-skill-update (#10) is NOT built yet. teach/onboard are specced against its documented contract but cannot RUN until it lands — build #10 first or in the same effort.
- Skill version-tracking surface and announce-skill-update internals are owned elsewhere (#10 + a version-tracking issue), not by teach/onboard.
- Reply on issue #10 to reconcile: guildmaster fulfills the broadcast ROLE via teach/onboard (agent-major), NOT a verb named announce-skill-update with #10's exact flag surface; coordinate the steward->guildmaster cutover on that basis. (Supersedes the now-stale v1.)
