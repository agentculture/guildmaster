# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.4] - 2026-05-28

### Added

- Register **`jetson`** (`agentculture/jetson`) as a downstream consumer in
  `docs/skill-sources.md`. Provisioned via `guild create --apply` from
  `culture-agent-template` — an agent + CLI for NVIDIA Jetson edge-AI ops
  (dist `jetson-cli`, command `jetson`).

## [0.6.3] - 2026-05-27

### Added

- **Registered `convertible`** (`agentculture/convertible`) in
  `docs/skill-sources.md` as a downstream consumer of the canonical kit —
  provisioned via `guild create --apply` from `culture-agent-template`. It is a
  swappable coder-agent harness that turns different models into repo workers
  behind one shared task contract — "the car around the model" (originating
  brief: [#34](https://github.com/agentculture/guildmaster/issues/34); handed to
  the new agent as
  [`convertible#1`](https://github.com/agentculture/convertible/issues/1)).

## [0.6.2] - 2026-05-26

### Added

- **Registered `dominion-breaker`** (`agentculture/dominion-breaker`) in
  `docs/skill-sources.md` as a downstream consumer of the canonical kit —
  provisioned via `guild create --apply` from `culture-agent-template`. It is an
  agentic CLI for cited monolith decomposition (originating brief:
  [#31](https://github.com/agentculture/guildmaster/issues/31)).

## [0.6.1] - 2026-05-26

### Added

- **Registered `agenda`** (`agentculture/agenda`) in `docs/skill-sources.md` as a
  downstream consumer of the canonical kit — the first sibling provisioned via
  `guild create --apply`.

### Fixed

- **`guild create` seed generator (`instantiate.py`)**: the CLAUDE.md/AGENTS.md
  seed emitted the agent name as a standalone emphasized line (`**<name>**`),
  tripping markdownlint **MD036** and failing the new repo's first CI run; the
  name is now inlined in a sentence.
- **`guild create` README rewrite**: `_set_readme_intro` only replaced the first
  line of the template's intro, leaving a dangling fragment when the intro spans
  multiple lines (as the real `culture-agent-template` intro does). It now
  replaces the whole first paragraph, stopping at a blank line **or** the start
  of a new markdown block (heading / list / blockquote / badge / code fence) so
  a block that immediately follows the intro is never silently dropped, while
  wrapped inline-code prose (a single leading backtick) is still consumed. Both
  bugs surfaced provisioning `agenda`; regression tests added.

## [0.6.0] - 2026-05-26

### Added

- **`guild create` — template-instantiate a new sibling repo.** Provisions a
  brand-new AgentCulture sibling by instantiating
  `agentculture/culture-agent-template` (overridable via `--template`),
  renaming identifiers throughout the clone (`culture_agent_template` → pkg,
  `culture-agent-template` → repo token), writing a self-init CLAUDE.md seed
  (carries a `/init` re-init instruction; satisfies `steward doctor`
  prompt-file-present + backend-consistency invariants), configuring the GitHub
  repo via `configure-repo.sh`, pushing the genesis commit, and registering the
  agent in `docs/skill-sources.md` (idempotent). Dry-run by default; `--apply`
  executes. `--json` emits a structured payload on both paths.
  - `guild/scaffold/instantiate.py` — the **pure** transform: `rename_map`,
    `transform_plan` (dry-run description), `transform_clone` (in-place);
    no network, no subprocess, fully unit-testable against a fixture dir.
  - `guild/cli/_commands/_provision_template.py` — injectable-runner executor
    with `preflight` (fail-fast: auth, existence, empty dest) and `apply`
    (gh→clone→transform→configure→commit→push).
  - `guild/cli/_commands/create.py` — CLI verb wiring argparse → plan → render
    | apply.
  - `.claude/skills/guild/scripts/create.sh` — thin wrapper (mirrors
    `overview.sh`).
  - 39 new tests covering: transform correctness, package-dir rename,
    identifier replacement everywhere, CLAUDE.md seed shape, dry-run
    external-free guarantee, `--apply` command sequence, fail-fast on existing
    repo / no auth / non-empty dest, ledger idempotency.

## [0.5.1] - 2026-05-24

### Changed

- **`docs/cutover.md` → complete.** The steward → guildmaster broadcaster cutover
  is done: guildmaster owns the supplier ledger and is the sole broadcaster;
  `--apply` is live. First post-cutover broadcast was the 2026-05-24 `guild teach`
  resync to 7 agents. Notes that steward's written records ([PR #62](https://github.com/agentculture/steward/pull/62),
  [#10](https://github.com/agentculture/guildmaster/issues/10)) still describe a
  partial handoff and are to be reconciled on steward's side.

## [0.5.0] - 2026-05-24

### Changed

- **steward → guildmaster cutover (guildmaster's side).** Migrated
  `docs/skill-sources.md` from the consumer-side "Upstream / Notes" view to the
  **supplier shape**: a canonical-set table with a "Downstream copies (known)"
  column (upstream reassigned `steward` → `guildmaster`), the devague-origin
  re-broadcast table, and a "Retained by steward" section recording the
  steward-specific skills (`org-overview`, steward's alignment `agent-config`
  variant, `discord-notify`, `jekyll-test`, `notebooklm`) that stay with steward.
  The downstream consumer lists were carried over verbatim from steward's ledger
  at cutover. This activates resync-detection in `teach` / `onboard` and
  skills-scoped drift in `guild overview --scope all` / `--scope self`
  ([issue #1 §1](https://github.com/agentculture/guildmaster/issues/1),
  `docs/cutover.md`).
- **`docs/cutover.md`** updated to the in-progress state: guildmaster's side is
  done and the handshake ping sent; the one remaining gate before `--apply` goes
  live is steward's ack that it has stopped broadcasting (no two live
  broadcasters, per [#10](https://github.com/agentculture/guildmaster/issues/10)).

## [0.4.2] - 2026-05-24

### Added

- **`guild overview --scope mesh`** — a live filesystem survey of the whole
  workspace, the answer to "what skills does every agent have, and what's
  missing or stale, and where" without waiting for the cutover. Discovers every
  agent (`<workspace>/*/culture.yaml`, via the new `discover_agents` helper) and
  reports, per agent, each canonical skill as **current** / **stale** (the
  agent's copy differs from guildmaster's by content fingerprint —
  `skill_fingerprint`) / **missing**, plus any non-canonical "extra" skills.
  Markdown + `--json`; `--workspace-root DIR` overrides the surveyed root
  (default: the parent of this repo). Read-only, inventory only — no
  dependency/relationship graph (that stays steward's lane). The existing
  ledger-based `--scope all` / `--scope self` are unchanged.

### Changed

### Fixed

- Mesh-survey robustness (Qodo review on #15): `discover_agents` and
  `iter_skills` now skip non-UTF-8 / unreadable `culture.yaml` and `SKILL.md`
  (one bad file in a surveyed repo no longer crashes the run), and
  `skill_fingerprint` skips symlinks (never follows links outside the skill dir;
  keeps the digest deterministic).

## [0.4.1] - 2026-05-24

### Added

- **`guild` skill** — the backing affordance + narration skill for `guild
  overview`, the supplier-overview half of the inventory split (sibling to the
  vendored `agent-config` skill that backs `guild show`). `scripts/overview.sh`
  is a deterministic wrapper that resolves how to invoke `guild` (installed →
  `uv` → `python -m guild`) and delegates to `guild overview`; `SKILL.md` is the
  **skills-scoped excerpt of steward's `org-overview` narration contract**
  ([#12](https://github.com/agentculture/guildmaster/issues/12),
  cite-don't-import): narrate three separated layers — observed facts, inferred
  relationships, suggestions (each naming its enacting `teach` / `onboard` /
  ledger command), reflect-only. Skills/version scope only — does NOT narrate
  steward's relationship-graph signals (`overlap` / `over-connected-agent` /
  `isolated-repo`). Recorded in `docs/skill-sources.md` as guildmaster-origin
  (not vendored).

### Changed

- `SELF_SKILLS` now includes `guild` — guildmaster's own affordance skill is
  excluded from the canonical kit it supplies to siblings (like `teach` /
  `onboard`), since it wraps the `guild` binary and is meaningless elsewhere.

### Fixed

## [0.4.0] - 2026-05-24

### Added

- **`guild overview`** — guildmaster's read-only skills-supplier overview surface
  ([#12](https://github.com/agentculture/guildmaster/issues/12)): the canonical
  skill set + versions/origins, the `docs/skill-sources.md` ledger view, and
  drift signals (unledgered skills, uncovered skills, per-agent kit gaps).
  `--scope all` (default) and `--scope self <agent>`; markdown or `--json`.
  Pure-Python, read-only — no `--apply`, no mutation, no LLM. Degrades
  gracefully pre-cutover: when the ledger has no downstream column the verb
  reports the canonical set and notes that drift activates after the
  steward→guildmaster cutover. Skills-scoped only — does not reproduce
  `steward overview`'s ecosystem relationship graph.
- **`guild show <path-or-suffix>`** — one agent's full config in one read-only
  view ([#12](https://github.com/agentculture/guildmaster/issues/12)): the
  detected system-prompt file (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`), the
  parallel `culture.yaml`, and the `.claude/skills` index. Path mode or suffix
  mode (resolved via `culture_server_yaml`). Target resolution happens once in
  Python; the human view shells out to the vendored `agent-config` `show.sh`
  (mirroring `steward show`), while `--json` emits a structured object (prompt
  file + contents, parsed `culture.yaml`, skills index) built natively. Failure
  output stays the structured `error:` / `hint:` shape. Inventory only — it
  reports, it does not judge drift.
- **`agent-config` skill** vendored from steward (cite-don't-import) to back
  `guild show`: `scripts/show.sh` + `data/backend-fingerprints.yaml` verbatim;
  SKILL.md reframed for guildmaster's inventory role + `type: command`. Recorded
  in `docs/skill-sources.md`; now part of the canonical skill set.
- `guild.skills.ledger.supplier_skills` / `consumer_map` — pure helpers that
  read the supplier ledger (skills tracked + their consumers) for `overview`.

### Changed

- `VERBS` index + `README.md` + `CLAUDE.md` document the new inventory verbs and
  the issue #12 division of labor (inventory → guildmaster; alignment judgment →
  steward).

## [0.3.0] - 2026-05-24

### Added

- **`guild teach`** — propagate a *set* of skills to a *set* of mesh agents.
  Agent-major: one GitHub issue per target agent, bundling a per-skill section
  for every taught skill (not one issue per skill). Skills are explicit
  (`--skill`, repeatable, or `--all`; no implicit default); targets from `--to`
  (bare names get `--org`) or the ledger's current consumers; new-vs-resync
  framing auto-detected per `(skill, agent)`. Dry-run by default; `--apply`
  files via the vendored `communicate` `post-issue.sh`.
- **`guild onboard`** — the new-sibling ceremony, built on the same engine as
  `teach`: the full canonical kit in new framing + an identity-setup section +
  idempotent ledger registration + a verification record (the pins to vendor).
  Inbound skills (the devague trio) carry an `agentculture/devague` origin
  block. Dry-run by default; `--apply` files the issue, writes the ledger,
  records the pins.
- **`/teach` and `/onboard` skill wrappers** (`.claude/skills/`) forwarding to
  the CLI verbs.
- `guild.skills` package — `ledger` (skill-sources parse + idempotent register),
  `sources` (script list + CHANGELOG excerpt), `render` (agent-major issue
  body), `identity` (onboarding identity-setup section).
- `docs/cutover.md` — the steward→guildmaster broadcaster cutover precondition
  (no `--apply` broadcasting before cutover; no two live broadcasters).

### Changed

- **`teach`/`onboard` supersede a separate `announce-skill-update` verb**
  ([#10](https://github.com/agentculture/guildmaster/issues/10) asked for one;
  guildmaster fulfills the broadcast *role* via these two agent-major verbs
  instead). README + CLAUDE.md document the supplier surface. Specced and
  planned via `/think` → `/spec-to-plan` (`docs/specs/`, `docs/plans/`).

## [0.2.0] - 2026-05-24

### Added

- **Vendored devague's three workflow skills** under `.claude/skills/` (cite,
  don't import) — `think` (idea→spec), `spec-to-plan` (spec→plan), and
  `assign-to-workforce` (plan→parallel implementation), the operator chain for
  the deterministic [`devague`](https://github.com/agentculture/devague) CLI.
  These flow the opposite direction of guildmaster's supplier role: `devague` is
  their author/upstream and `steward` re-broadcasts them to the mesh. Vendored
  from steward's copy at `914d5ca`, which tracks devague `0.11.1` (`c04b595`,
  MIT). Resolves [#5](https://github.com/agentculture/guildmaster/issues/5),
  [#6](https://github.com/agentculture/guildmaster/issues/6), and
  [#7](https://github.com/agentculture/guildmaster/issues/7).
- `docs/skill-sources.md` — guildmaster's provenance ledger, scoped to what it
  vendors as a consumer: the canonical set (upstream `steward`) and the inbound
  devague trio (origin `devague`, re-broadcast via `steward`). The upstream
  ledger/broadcast ownership migrates here later, per the issue #1 division of
  labor.

### Changed

- The three vendored SKILL.md files carry a `type: command` frontmatter
  divergence from their verbatim devague upstream: culture/agex's
  `core.skill_loader` requires `name` + `description` + `type:`, and a type-less
  SKILL.md is silently skipped by `backends/claude_code/probe.py`. guildmaster
  declares an agent in `culture.yaml`, so the addition is load-bearing on the
  culture backend and harmless on `claude-code`.

## [0.1.0] - 2026-05-24

### Added

- Initial scaffold onboarding guildmaster to the AgentCulture sibling pattern
  ([issue #1](https://github.com/agentculture/guildmaster/issues/1)).
- `guild` Python package (`guild-cli` on PyPI) with the afi-cli CLI layout:
  `cli/_errors.py` (typed `GuildError` + exit-code policy), `cli/_output.py`
  (stdout/stderr split, `--json`), `cli/_repo.py` (offline repo/skill helpers),
  and an argparse dispatcher. `python -m guild` runs.
- Agent-first verbs `whoami` (identity probe), `learn` (repo survey), and
  `explain` (per-skill / per-verb detail) — all read-only, offline, and
  deterministic.
- Vendored the canonical skill set under `.claude/skills/` (cite, don't
  import): `cicd`, `communicate`, `version-bump`, `run-tests`, `sonarclaude`,
  `doc-test-alignment`, and `pypi-maintainer`. The `communicate` broadcast
  templates are repointed from steward to guildmaster as the supplier.
- `culture.yaml` declaring the `guildmaster` agent on the `claude` backend,
  alongside the existing `CLAUDE.md` runtime prompt.
- Tooling: `pyproject.toml` (hatchling), `.flake8`,
  `.claude/skills.local.yaml.example`, `CHANGELOG.md`, and CI workflows
  (`tests.yml` + `publish.yml` via PyPI Trusted Publishing).
- pytest suite covering the CLI surface, each verb, the skills-convention
  invariant, and the version fallback.

### Changed

### Fixed
