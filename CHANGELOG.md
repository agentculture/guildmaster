# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
