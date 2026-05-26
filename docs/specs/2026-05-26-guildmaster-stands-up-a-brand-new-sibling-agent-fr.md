# guildmaster stands up a brand-new sibling agent from one request: a single command creates the public, MIT-licensed, Python repo on GitHub, clones it into the workspace, vendors the full canonical skill kit directly into .claude/skills/, writes a valid CLAUDE.md + culture.yaml identity, and registers it in the ledger — no hand-built scaffold, no issue round-trip

> guildmaster stands up a brand-new sibling agent from one request: a single command creates the public, MIT-licensed, Python repo on GitHub, clones it into the workspace, vendors the full canonical skill kit directly into .claude/skills/, writes a valid CLAUDE.md + culture.yaml identity, and registers it in the ledger — no hand-built scaffold, no issue round-trip

## Audience

- AgentCulture supplier operators (the human operator + the guildmaster agent acting for them) standing up new sibling repos that guildmaster's GitHub account can directly create and write

## Before → After

- Before: new siblings are hand-built today (the appsec agent was scaffolded manually on an onboarding/sibling-scaffold branch) or onboarded via a GitHub-issue brief the target's OWN agent must implement; there is no one-shot path where guildmaster itself provisions the repo
- After: one command turns a {name, description} request into a fully-scaffolded, skills-equipped sibling: a public MIT Python repo on GitHub + a local clone in the workspace, kit copied in, identity files written, ledger updated — ready for that agent's own resident agent to take over its domain logic

## Why it matters

- provisioning siblings IS guildmaster's supplier job; doing it by hand is slow, drifts from the canonical kit, and doesn't reliably pass steward doctor. A reproducible one-shot makes the supplier role real and the kit consistent from birth

## Requirements

- safe-by-default: dry-run renders exactly what it WOULD do (repo spec, file manifest, generated CLAUDE.md/culture.yaml, ledger diff) and touches nothing external; --apply performs the irreversible acts (gh repo create, git clone, file writes, ledger commit)
  - honesty: in dry-run, zero gh/git network calls and zero file writes happen outside .devague — verifiable by running dry-run with no network
- the local clone lands in the workspace root (guildmaster's parent dir), resolved PORTABLY via skills.local.yaml / --workspace-root — never a hardcoded home path (steward doctor portability invariant)
  - honesty: no tracked file or generated output holds an absolute home path; the clone dir resolves from config/flag, falling back to the guildmaster repo's parent
- the skill kit is COPIED directly into the new repo's .claude/skills/ (file copy of each canonical skill dir, inbound-origin attribution preserved), not rendered as a GitHub issue
  - honesty: each .claude/skills/<name>/ dir in the new repo is content-identical to guildmaster's canonical copy (minus git-ignored local files); inbound skills keep origin attribution
- generated identity files (CLAUDE.md, culture.yaml, skills.local.yaml.example) must satisfy steward doctor's prompt-file-present, backend-consistency, skills-convention and portability invariants on first run
  - honesty: steward doctor --scope self on the fresh clone reports prompt-file-present, backend-consistency, skills-convention, and portability all green
- the CLAUDE.md guildmaster writes is a self-initializing SEED, not a final runtime prompt: it carries the agent's --desc and an explicit instruction for the new agent to re-init its own CLAUDE.md from that description + the scaffolded repo (an /init-style bootstrap). guildmaster scaffolds the prompt frame + identity; the agent fills in its domain. The seed must still pass steward doctor (prompt-file-present + backend-consistency)
  - honesty: a freshly-created repo's CLAUDE.md (a) names the agent and embeds its --desc, (b) carries an explicit, actionable re-init instruction, and (c) passes steward doctor prompt-file-present + backend-consistency BEFORE any re-init is run

## Honesty conditions

- an end-to-end --apply run produces a clone that passes 'steward doctor --scope self <clone>' with zero failures
- the verb needs only credentials guildmaster already holds (a gh login that can create repos in the target org) — no new auth surface; if it can't create the repo it fails fast with a clear error, not a half-built scaffold
- after --apply the new agent's resident agent starts with zero manual kit/identity setup: the repo already builds, tests pass, and steward doctor is green
- the manual appsec scaffold (the onboarding/sibling-scaffold branch) is reproducible by the verb — every step done by hand there maps to something the verb does automatically
- two siblings created by the verb get byte-identical kit + structurally-identical identity files (no per-run drift) — reproducibility is observable, not asserted
- the verb refuses / no-ops on a target that already exists or is outside the AgentCulture-sibling shape, rather than scaffolding arbitrary content into it
- the appsec acceptance check is automatable: a test asserts repo-exists + license==MIT + description-set + kit-complete + steward-doctor-green for a scratch target run

## Success signals

- running the verb --apply against agentculture/appsec yields: repo exists on GitHub (public, MIT, description set), local clone in workspace, full canonical kit under .claude/skills/, a CLAUDE.md + culture.yaml that pass 'steward doctor --scope self', and an updated docs/skill-sources.md ledger entry — reproducing/superseding the manual appsec scaffold

## Scope / boundaries

- scaffolds AgentCulture siblings only — the canonical kit + identity, not arbitrary Python apps; does NOT replace the issue-based onboard for repos guildmaster can't directly write; does NOT author the new agent's domain logic

## Decisions

- the surface is a NEW top-level verb 'guild create' (not a mode on onboard); it reuses the kit+ledger engine but keeps the irreversible external-side-effect path distinct from the issue-based onboard
- v1 scaffolds the FULL afi-cli skeleton: pyproject, package dir, __init__/__main__, argparse cli chassis, tests, .github tests+publish workflows, CHANGELOG, README, LICENSE — a runnable CI-green repo from birth, plus kit+identity
- on --apply the genesis commit is pushed to main on the brand-new repo (nothing to clobber); dry-run still writes/pushes nothing external
