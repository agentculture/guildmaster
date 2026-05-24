# Build Plan — guildmaster ships /teach and /onboard: two agent-first verbs layered over its announce-skill-update broadcast. 'guild teach' pushes a chosen SET of skills to a chosen SET of mesh agents in one command; 'guild onboard' welcomes a brand-new sibling agent with the full canonical skill kit, an identity-setup brief, ledger registration, and post-onboard verification. Both default to dry-run; --apply files the issues.

slug: `guildmaster-ships-teach-and-onboard-two-agent-firs` · status: `exported` · from frame: `guildmaster-ships-teach-and-onboard-two-agent-firs`

> guildmaster ships /teach and /onboard: two agent-first verbs layered over its announce-skill-update broadcast. 'guild teach' pushes a chosen SET of skills to a chosen SET of mesh agents in one command; 'guild onboard' welcomes a brand-new sibling agent with the full canonical skill kit, an identity-setup brief, ledger registration, and post-onboard verification. Both default to dry-run; --apply files the issues.

## Tasks

### t1 — Supplier-surface architecture docs: document guild teach + guild onboard in README.md and CLAUDE.md

- covers: c1, c9, h13, c25, h15
- acceptance:
  - README.md and CLAUDE.md document guild teach + guild onboard, the agent-major one-issue-per-agent model, and the decision that they supersede a separate announce-skill-update verb
  - Docs state the before (no guildmaster broadcast verb today; steward broadcasts) and the after (one command propagates a skill set / onboards a sibling)

### t2 — Ledger module: parse skill-sources.md consumers and register a new consumer idempotently

- covers: c18, h4
- acceptance:
  - parse(skill) returns downstream consumers via comma-split + first-backtick-token per chunk; em-dash, hyphen, or empty cell yields an empty list; skill membership matched by backticked name in the first cell
  - register(agent) adds the agent to the downstream column of every canonical skill row; a second run changes zero bytes (idempotent, no duplicates)

### t3 — Source extractors: top-level scripts listing and CHANGELOG excerpt

- acceptance:
  - script list returns only top-level files under skill/scripts sorted, skipping subdirectories such as templates
  - CHANGELOG excerpt with --since X slices top-down excluding the [X] heading and errors if [X] is absent; without --since it returns blocks mentioning the skill name

### t4 — Identity-setup section renderer for onboarding briefs

- covers: c20, h6
- acceptance:
  - identity section enumerates culture.yaml + backend + a recognized prompt file so a sibling that follows it would satisfy steward doctor prompt-file-present and backend-consistency

### t5 — Cutover precondition doc + draft reply on issue #10 reconciling the broadcast role

- covers: c13, h14
- acceptance:
  - a documented precondition states teach/onboard must not broadcast in production before the steward to guildmaster cutover (no two live broadcasters)
  - a drafted #10 reply explains guildmaster fulfills the broadcast role via teach/onboard (agent-major), not a verb named announce-skill-update with #10 exact flag surface

### t6 — Agent-major rendering engine: compose per-skill sections into one issue per agent, with new/resync framing and origin attribution

- depends on: t2, t3
- covers: c26, h9, c19, h5
- acceptance:
  - rendering skills [A,B] for one agent yields ONE issue body containing an A section and a B section, verifiable on the markdown with no posting
  - framing per (skill, agent) is resync when the agent already appears in that skill ledger downstream, new otherwise; never a new section to an existing consumer nor a resync to a stranger
  - the devague trio (think, spec-to-plan, assign-to-workforce) sections carry the agentculture/devague origin block

### t7 — guild teach CLI verb: loop the render engine over a skill set and target set, dry-run by default

- depends on: t6
- covers: c7, h12, c28, h16, c21, h7
- acceptance:
  - guild teach --skill cicd --skill communicate --to tipalti (dry-run) prints ONE issue for tipalti with both sections, exits 0, posts nothing and mutates no file
  - bare invocation with no --skill and no --all exits non-zero with a hint; --all selects the canonical set explicitly
  - with --apply teach posts one issue per agent via the vendored communicate post-issue.sh and exits non-zero if any post fails; targeting resolves from --to, falling back to the ledger per skill

### t8 — guild onboard CLI verb: full canonical kit in new framing + ledger registration + identity section + verification record

- depends on: t6, t2, t7, t4
- covers: h8, c27, h10, c29, h17
- acceptance:
  - guild onboard --agent agentculture/newsib (dry-run) prints ONE consolidated issue (all canonical sections plus identity section) plus an unapplied ledger diff plus a verification record, writing nothing
  - onboard composes teach for the full canonical set in new framing; onboard adds only kit-selection, ledger registration and the verification record (no separate broadcast path)
  - with --apply onboard files the one issue, registers newsib in the ledger idempotently, records the pins; devague trio carries the agentculture/devague origin

### t9 — /teach skill wrapper (SKILL.md + scripts/teach.sh)

- depends on: t7
- covers: c6, h11
- acceptance:
  - skill dir teach has SKILL.md whose frontmatter name equals the directory and a sibling scripts/teach.sh forwarding to guild teach; the description names the audience (supplier operators targeting mesh sibling agents)
  - passes the skills-convention invariant (SKILL.md has a sibling scripts/ and matching frontmatter name)

### t10 — /onboard skill wrapper (SKILL.md + scripts/onboard.sh)

- depends on: t8
- acceptance:
  - skill dir onboard has SKILL.md whose frontmatter name equals the directory and a sibling scripts/onboard.sh forwarding to guild onboard; passes the skills-convention invariant

## Risks

- [unknown_nonblocking] Rendering lifts steward announce templates from the vendored communicate skill as per-skill sections; if those templates are absent or incompatible, the render task is blocked (task t6)
- [follow_up] Going live is gated on the steward to guildmaster cutover (cutover task); do not enable --apply broadcasting in production before cutover
- [unknown_nonblocking] agtag must be on PATH for --apply posting; dry-run paths and their tests must not require agtag (task t7)
