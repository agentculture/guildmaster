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

## Division of labor with steward (decided)

guildmaster exists to **take skills work off steward**, and the split (issue #1
§1) is settled: **guildmaster becomes the skills supplier/manager.** It takes
ownership of —

- the **canonical upstream skill set** (the source-of-truth copies);
- the **upstream/downstream ledger** (`skill-sources.md`, migrating from
  steward — see below);
- the **broadcast verb** (`announce-skill-update`) that notifies consumers when
  a skill changes; and
- **skill version tracking**.

**steward retreats to agent-alignment** — `steward doctor` (sibling health /
compliance) and `steward overview` (ecosystem sense-making) stay with steward.
This change is recorded on issue #1; until guildmaster's supplier surface
actually ships, steward continues to hold the live ledger and broadcast so the
mesh isn't left without an owner mid-migration (no two competing ledgers).

**Transition path — onboard as a consumer first.** Before building the supplier
layer, guildmaster vendors the canonical skills like every other sibling: you
cannot credibly *manage* the skill stack until you *run* it yourself. The
ledger, broadcast, and version-tracking responsibilities transfer from steward
once the consuming + managing surface is in place.

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

**Supplier verbs — `teach` & `onboard` (the broadcast surface).** As the mesh's
skills supplier, guildmaster propagates skills through two write verbs:

- `guild teach --skill <name> … --to <agent> …` — teach a **set** of skills to a
  **set** of agents.
- `guild onboard --agent <owner/repo>` — onboard a **new** sibling: the full
  canonical kit + an identity-setup section + ledger registration + a
  verification record.

They are **agent-major**: one issue per target agent, bundling a per-skill
*section* for each skill that agent receives — *not* one issue per skill.
New-vs-resync framing is auto-detected per `(skill, agent)` from
`docs/skill-sources.md`; skills must be selected explicitly (`--skill` /
`--all`, no implicit default). `teach` is the single render+post engine and
`onboard` composes it (`onboard X` ≡ `teach <all-canonical> --new --to X` +
ledger + identity + verification). **These supersede a separate
`announce-skill-update` verb** ([issue #10](https://github.com/agentculture/guildmaster/issues/10)
asked for one; guildmaster fulfills the broadcast *role* via these two instead).
Going live is gated on the steward→guildmaster cutover (`docs/cutover.md`) — no
two live broadcasters.

**Provisioning verb — `guild create` (template-instantiate a new sibling).**

- `guild create --agent OWNER/REPO --desc TEXT [--backend claude|acp] [--workspace-root DIR] [--template agentculture/culture-agent-template] [--dist NAME] [--apply] [--json]` — provision a brand-new AgentCulture sibling by instantiating the GitHub template, renaming identifiers throughout the clone, writing a self-init CLAUDE.md seed, configuring the GitHub repo (branch protection, environments, SONAR_TOKEN placeholder), pushing the genesis commit, and registering the agent in `docs/skill-sources.md`. Dry-run by default; `--apply` executes. The transform is **pure** (unit-testable against a fixture dir; no network): `culture_agent_template` → pkg (underscore form, e.g. `my_agent`), `culture-agent-template` → repo token (hyphen form, e.g. `my-agent`). `--dist NAME` sets the **PyPI distribution name** (default: the repo token); pass e.g. `--dist jetson-cli` to publish as `jetson-cli` while keeping the command and import package as the repo token (`jetson`) — this retargets only `[project].name`, the `importlib.metadata` lookup, and the TestPyPI install pin, matching the `guild-cli`/`guild` convention without a manual post-create edit. (Renaming the dist needs a matching Trusted Publisher registered for that project name on PyPI/TestPyPI — `guild create` configures the GitHub side only.) The CLAUDE.md seed is a `/init`-style bootstrap placeholder — run `/init` in the new repo after provisioning to expand it into a full runtime prompt. Implementation: `guild/scaffold/instantiate.py` (pure transform), `guild/cli/_commands/create.py` (CLI), `guild/cli/_commands/_provision_template.py` (injectable-runner executor), `.claude/skills/guild/scripts/create.sh` (thin wrapper).

**Inventory verbs — `overview` & `show` (the read-only surfaces).** guildmaster
owns the mesh's *inventory* surfaces per
[issue #12](https://github.com/agentculture/guildmaster/issues/12) — the
"what kit + config does an agent have?" view. The dividing rule from issue #12:
**inventory → guildmaster; judgment ("how do agents relate / are they aligned?")
→ steward.** Neither verb clones `steward overview`'s relationship graph.

- `guild overview [--scope all|self <agent>|mesh]` — the supplier view:
  canonical skill set + versions/origins, the `docs/skill-sources.md` ledger,
  and drift signals (uncovered skills, per-agent kit gaps). Pure-Python,
  read-only, **no `--apply`**. Pre-cutover the ledger has no downstream column,
  so `--scope all`/`self` drift is inactive and the verb says so (reads
  whichever ledger is authoritative). `--scope mesh` is the ledger-free
  alternative: it surveys every agent in the workspace
  (`<workspace>/*/culture.yaml`) live off the filesystem and reports, per agent,
  each canonical skill as current / **stale** (content fingerprint differs from
  guildmaster's copy) / **missing** — answering "what's missing or stale, and
  where" today. Still inventory only — no relationship graph.
- `guild show <path-or-suffix>` — one agent's full config: detected prompt file
  (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`), parallel `culture.yaml`, and the
  `.claude/skills` index. Thin wrapper that shells out to the vendored
  `agent-config` skill's `show.sh` (cite-don't-import from steward), mirroring
  `steward show`. Path mode or suffix mode (resolved via `culture_server_yaml`).

Both **report**; they do not flag or fix drift (that judgment is steward's lane).

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

**Canonical skill set to vendor** (steward holds the current canonical copies;
copy from `../steward/.claude/skills/<name>/`): `cicd` (PR lifecycle),
`communicate` (cross-repo issue I/O + mesh messaging), `version-bump`,
`run-tests`, `sonarclaude` (SonarCloud gate), and `doc-test-alignment` (stub
today — vendor to be ready). For a PyPI-published CLI, also vendor
`pypi-maintainer`. The upstream/downstream map is `skill-sources.md` — today
steward's (`../steward/docs/skill-sources.md`, or
<https://github.com/agentculture/steward/blob/main/docs/skill-sources.md> for a
standalone clone); per the decided division of labor it **migrates to
guildmaster**, which becomes the upstream owner. During the transition, vendor
from steward's current copies and treat its ledger as source of truth until
ownership transfers. Once guildmaster owns the broadcast, `announce-skill-update`
moves here too; until then steward still auto-files migration briefs on this
repo when a vendored skill changes.

## `steward doctor` invariants (build to pass these)

- **portability** — no absolute user-home paths in tracked files, and no
  per-user home-directory dotfile config references in committed
  `.md`/`.yaml`/`.toml`/`.json` (outside documented carve-outs). Commit a
  repo-local config or document a portable lookup instead.
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
