# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**guildmaster** is *an agent and CLI that manages skills* — skill and
skillversion management plus an overview surface for the AgentCulture mesh. It
is a sibling to [`steward`](https://github.com/agentculture/steward) (resident-agent
alignment), [`culture`](https://github.com/agentculture/culture) (the IRC-based
agent mesh), and [`daria`](https://github.com/agentculture/daria) (the awareness
agent) in the broader Organic Development framework. See the workspace-level
`CLAUDE.md` (one directory above this repo, when present) for the cross-project
overview and the all-backends rule that governs Culture.

The authoritative onboarding brief for this repo is
[**issue #1**](https://github.com/agentculture/guildmaster/issues/1), filed by
`steward`. It is self-contained and is the source of truth for the target shape
described below. `steward` is the reference exemplar — when in doubt, copy from
it. Sibling paths in this file (e.g. `../steward/`) **assume the workspace
layout** where siblings are checked out in the same parent directory; in a
standalone clone, read the same files at
<https://github.com/agentculture/steward> or clone steward beside this repo
first. Each such path below names the project, not a guaranteed location.

## Current state vs. target

**This repo is currently a skeleton** (`LICENSE`, `README.md`, `.gitignore`,
and this `CLAUDE.md`). There is no Python package, CLI, tests, or skills yet.
Everything under "Project shape" and "Build / test / publish" below describes
the **target** the resident agent is scaffolding toward, per issue #1 — do not
assume those files exist until you have created them.

## The open coordination question (settle before going deep)

guildmaster exists to **take skills work off steward** — but that overlaps
steward's current role, and **the division of labor is not yet settled**. Before
building the management/supplier layer, the call must be made explicitly (reply
on issue #1 or open one on `agentculture/steward`):

- **steward owns today:** the canonical upstream skill set, the
  upstream/downstream ledger (`../steward/docs/skill-sources.md`), the broadcast
  verb (`steward announce-skill-update`), and the overview surface
  (`steward overview` / `steward doctor`).
- **The fork:** does guildmaster *become* the supplier/manager (taking the
  ledger + broadcast + version tracking, steward retreating to
  agent-alignment), or *complement* steward (guildmaster owns skill
  **versioning** + a richer **overview**, steward keeps the ledger)? This decides
  who is upstream for what.

Until that lands, guildmaster onboards as a **consumer** sibling (vendor the
canonical skills like every other sibling). That is the correct first step
regardless of outcome — you cannot credibly *manage* the skill stack until you
*run* it yourself.

## Project shape (target — afi-cli pattern, no `src/`)

Distributed as **`guild-cli`** on PyPI via Trusted Publishing (PyPI **and**
TestPyPI projects are already set up); Python package `guild`; binary `guild`.
The repo and the Culture agent are named `guildmaster`; the CLI ships under the
shorter `guild` name. Following steward's layout:

```text
guild/                      # Python package
├── __init__.py             # __version__ via importlib.metadata("guild-cli")
├── __main__.py             # python -m guild
└── cli/
    ├── __init__.py         # argparse main()
    ├── _errors.py          # typed error + EXIT_USER_ERROR / EXIT_ENV_ERROR
    ├── _output.py          # emit_result / emit_error (stdout/stderr split, --json)
    └── _commands/          # one module per subcommand: register(sub) + handler
tests/                      # pytest suite (tests/test_cli_*.py)
.claude/skills/<name>/      # SKILL.md + scripts/ per skill (see Skills convention)
.github/workflows/          # tests.yml + publish.yml (OIDC Trusted Publishing)
culture.yaml                # declares the agent + backend
pyproject.toml              # hatchling backend; version source-of-truth
CHANGELOG.md                # Keep-a-Changelog
```

**Agent-first verbs:** the CLI scaffold ships `whoami` (smallest auth probe),
`learn`, and `explain` (the agent-affordance verbs). **Any write verb defaults
to dry-run; `--apply` commits** — agents call CLIs in loops, so safe-by-default
is mandatory.

**Backend:** guildmaster is a CLI *plus* an agent like steward, so the natural
fit is `backend: claude` with this `CLAUDE.md` as the runtime prompt and a
`culture.yaml` declaring the `guildmaster` agent suffix (steward's is
`agents:\n- suffix: steward\n  backend: claude`). If instead it runs on a
locally-hosted model via `acp`, the runtime prompt is `AGENTS.md` and
`culture.yaml` declares `backend: acp` + `model:` + inline `system_prompt` +
`acp_command` (`daria` is the worked example). Keep the prompt file and
`culture.yaml` consistent — that is the backend-consistency invariant.

## Build / test / publish (target toolchain, matching steward)

- **Install for dev:** `uv sync` (or `uv pip install -e .` then `uv pip install --group dev`).
- **Run CLI from source:** `uv run guild --version` / `uv run python -m guild ...`.
- **Tests:** `uv run pytest -n auto -v`. Single test: `uv run pytest tests/test_cli_foo.py::test_bar -v`. CI runs on every PR + push to main.
- **Version bump:** `python3 .claude/skills/version-bump/scripts/bump.py {patch|minor|major}` — updates `pyproject.toml` and prepends a CHANGELOG entry. **Required on every PR** (the `version-check` CI job fails the run if the version matches main — AgentCulture rule, no exceptions for docs/config-only changes).
- **Lint:** `flake8`, `bandit -r guild/`, `black`, `isort` (run via `uv run`); `markdownlint-cli2` against a repo-local `.markdownlint-cli2.yaml`. Don't depend on per-user home-directory configs.
- **Publish:** push to `main` triggers `publish.yml` → `uv build` → publishes `guild-cli` to PyPI via Trusted Publishing (no API tokens; the PyPI + TestPyPI projects are already provisioned). PRs publish a `.dev<run_number>` to TestPyPI. Fork PRs are skipped (no OIDC context).

## Finishing a branch: default to a PR

When work on a branch is complete and tests pass, **push the branch and open a
Pull Request** via the `cicd` skill (`workflow.sh open` / `agex pr open`) — do
not pause on an interactive "what next?" menu. This is the integration point for
the whole `branch → implement → bump version → PR` workflow, and it overrides
the Superpowers `finishing-a-development-branch` skill's default pause.
Merge-locally / keep-as-is / discard remain available only when the user asks.

## Skills convention (cite, don't import)

Skills are **copied** into `.claude/skills/<name>/` — guildmaster owns its copy;
nothing is symlinked or installed as a cross-repo dependency. Each skill ships:

1. `SKILL.md` — *why* and *when* to use it (frontmatter + short prose). The
   frontmatter `name` **must equal the directory name**.
2. `scripts/<entry-point>.(sh|py)` — the automation. Following a skill should be
   "run this script," not ten manual steps.
3. **No external path dependencies** — scripts must not reach into another
   skill's copy or any path outside this repo. Vendor what you need so skills
   stay portable.

Per-machine paths live in `.claude/skills.local.yaml` (git-ignored); a committed
`.claude/skills.local.yaml.example` documents every key. Skills read the local
file, falling back to the example.

**Canonical skill set to vendor** (steward is upstream for all six; copy from
`../steward/.claude/skills/<name>/`): `cicd` (PR lifecycle), `communicate`
(cross-repo issue I/O + mesh messaging), `version-bump`, `run-tests`,
`sonarclaude` (SonarCloud gate), and `doc-test-alignment` (stub today — vendor
to be ready). For a PyPI-published CLI, also vendor `pypi-maintainer`. The
upstream/downstream map is steward's `docs/skill-sources.md`
(`../steward/docs/skill-sources.md`, or
<https://github.com/agentculture/steward/blob/main/docs/skill-sources.md> for a
standalone clone) — treat it as the source of truth when vendoring. When steward
ships a skill change, it auto-files a migration brief on this repo via
`steward announce-skill-update`.

## `steward doctor` invariants (build to pass these)

- **portability** — no `/home/<user>/...` paths in tracked files; no `~/.<dotfile>`
  config refs in committed `.md`/`.yaml`/`.toml`/`.json` (outside documented carve-outs).
- **skills-convention** — every `.claude/skills/<name>/SKILL.md` has a sibling
  `scripts/` directory and matching frontmatter `name`.
- **prompt-file-present** — a repo declaring an agent in `culture.yaml` has a
  recognized system-prompt file.
- **backend-consistency** — the declared `backend` agrees with the prompt files
  on disk (don't declare `backend: claude` with only an `AGENTS.md`).

Check guildmaster against these with `steward doctor --scope self <path-to-guildmaster>`,
run from a steward checkout (`../steward` under the workspace layout; otherwise
clone <https://github.com/agentculture/steward> or use an installed `steward`
CLI). steward runs its own vendored portability check against the target, so
guildmaster doesn't need to vendor it first.
