# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-05-24

### Added

- `docs/skill-sources.md` now records guildmaster's **downstream broadcasts** of
  the devague trio (`think`, `spec-to-plan`, `assign-to-workforce`). guildmaster
  re-broadcast the trio to 17 skill-vendoring agent repos on 2026-05-24 (one
  combined "vendor the trio" issue per repo, via the `communicate` skill, origin
  attributed to `agentculture/devague`), and the ledger lists each repo + issue.
  This is guildmaster's first act as the trio's mesh re-broadcaster, ahead of the
  formal supplier-role transfer — the `announce-skill-update` verb + ledger
  handoff is tracked in
  [steward#60](https://github.com/agentculture/steward/issues/60).

### Changed

### Fixed

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
