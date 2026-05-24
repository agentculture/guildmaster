# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
