# Skill supplier — guildmaster's canonical skills

guildmaster is the AgentCulture mesh's **skill supplier/manager**. Per the
settled division of labor ([issue #1 §1](https://github.com/agentculture/guildmaster/issues/1))
and the completed steward → guildmaster cutover (`docs/cutover.md`), guildmaster
owns the canonical upstream copies of the cross-sibling skill set, this
upstream/downstream ledger, the broadcast verbs (`teach` / `onboard`), and skill
version tracking. `steward` has retreated to agent-alignment (`steward doctor` /
`steward overview`) and is no longer the live broadcaster.

This file is the deterministic upstream/downstream map handed over from
steward's `docs/skill-sources.md` at cutover. Each skill has exactly one
canonical source repo (the **upstream/origin** column); other repos hold
downstream copies that may lag and should periodically re-sync from upstream.
`guild teach` / `guild onboard` read the **Downstream** column to auto-frame each
`(skill, agent)` as *new* vs *resync*, and `guild overview` reads it for
skills-scoped drift.

Everything here follows **cite, don't import**: each skill is *copied* into
`.claude/skills/<name>/`, not symlinked or installed as a cross-repo dependency.
Each consumer owns its copy and may diverge; nothing reaches across skill
boundaries at runtime. When upstream changes, downstream copies do **not**
auto-update — re-sync explicitly from the cited source.

## Canonical supplied skills (upstream = `guildmaster`)

These are the cross-sibling skills guildmaster owns and broadcasts. Source of
truth is guildmaster's own copy under `.claude/skills/<name>/`; downstream
consumers re-sync from there. Ownership transferred from `steward` at cutover;
the downstream lists below were carried over from steward's ledger and are kept
current by `guild overview --scope mesh`.

| Skill | Upstream | Downstream copies (known) | Notes |
|-------|----------|---------------------------|-------|
| `agent-config` | `guildmaster` (`.claude/skills/agent-config/`) | `agenda`, `dominion-breaker`, `convertible`, `jetson` | Inventory variant backing `guild show` ([#12](https://github.com/agentculture/guildmaster/issues/12)); `show.sh` + `data/backend-fingerprints.yaml` vendored verbatim from steward, SKILL.md reframed from alignment-judgment to inventory + `type: command` added. **Forked from steward:** steward retains its own alignment-focused `agent-config` variant; the inventory variant is guildmaster's to supply. |
| `cicd` | `guildmaster` (`.claude/skills/cicd/`) — layered on `agex pr` (in `agentculture/agex-cli`) | `afi-cli`, `agex-cli` (adapted-thin delegate — owns `agex pr`; see [agex-cli#53](https://github.com/agentculture/agex-cli/pull/53)), `agtag`, `antoine`, `appsec`, `auntiepypi`, `cfafi` (still named `pr-review`), `code-lens-cli`, `culture` (still named `pr-review`), `devague`, `katvan`, `lecodeur`, `lepenseur`, `seer-cli`, `telek`, `agenda`, `dominion-breaker`, `convertible`, `jetson`, `grant` (still named `pr-review`) | Thin delegate to `agex pr` for lint / open / read / reply / delta, plus guildmaster's `status` (SonarCloud quality gate + hotspots + unresolved-thread tally) and `await` (composes `agex pr read --wait` with `status`, non-zero exit on Sonar ERROR / unresolved threads) extensions. **Inverted case:** agex-cli, as the `agex pr` upstream, vendors the skill adapted-thin — a `workflow.sh`-only pure delegate ([agex-cli#53](https://github.com/agentculture/agex-cli/pull/53)). Renamed from `pr-review` in steward 0.7.0; downstream copies may keep the old name on their own cadence. |
| `communicate` | `guildmaster` (`.claude/skills/communicate/`) | `afi-cli`, `agex-cli` (identifier-only — vendored steward 0.11.0; scripts current as of 0.18.0), `agtag`, `antoine`, `appsec`, `auntiepypi`, `code-lens-cli`, `culture` (still named `coordinate`), `devague`, `katvan`, `lecodeur`, `lepenseur`, `seer-cli`, `telek`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | Cross-repo + mesh communication: file issues / hand off briefs to sibling-repo agents (auto-signed), comment on existing issues, fetch issues to inline state into briefs, and send live messages to Culture mesh channels (unsigned — nick is the speaker). Renamed from `coordinate` in steward 0.8.0; absorbed `gh-issues` (as `fetch-issues.sh`) in 0.9.1. Issue I/O backed by `agtag` (>=0.1) since steward 0.11.0 — signature resolves from local `culture.yaml` (override via `--as`). |
| `doc-test-alignment` | `guildmaster` (`.claude/skills/doc-test-alignment/`) | `devague`, `lecodeur`, `lepenseur`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | Stub; real implementation TBD. `scripts/check.sh` exits not-yet-implemented today. |
| `pypi-maintainer` | `guildmaster` (`.claude/skills/pypi-maintainer/`) | `agtag`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | Switches a PyPI package install between pypi / test-pypi / local. Generalised from the original culture-specific `change-package`. |
| `run-tests` | `guildmaster` (`.claude/skills/run-tests/`) | `agtag`, `antoine`, `appsec`, `code-lens-cli`, `culture`, `culture-sonar-cli`, `devague`, `lecodeur`, `lepenseur`, `seer-cli`, `grant`, `telek`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | Coverage source resolves from `[tool.coverage.run]` in `pyproject.toml`, so the script is portable across siblings without modification. |
| `sonarclaude` | `guildmaster` (`.claude/skills/sonarclaude/`) | `antoine`, `appsec`, `code-lens-cli`, `devague`, `lecodeur`, `lepenseur`, `seer-cli`, `telek`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | SonarCloud API client. Project key resolves from `$SONAR_PROJECT` or `--project KEY`. |
| `version-bump` | `guildmaster` (`.claude/skills/version-bump/`) | `afi-cli`, `agtag`, `antoine`, `appsec`, `auntiepypi`, `cfafi`, `code-lens-cli`, `culture`, `devague`, `lecodeur`, `lepenseur`, `seer-cli`, `grant`, `telek`, `agenda`, `dominion-breaker`, `convertible`, `jetson` | Pure Python, prepends a Keep-a-Changelog entry; no per-repo customization needed. |

> **How the downstream column is maintained.** The "Downstream copies (known)"
> entries are kept in sync with guildmaster's own drift detector:
> `guild overview --scope mesh` walks every workspace repo that declares an agent
> (`culture.yaml`) and reports, per agent, each canonical skill as current /
> stale / missing. Two classes carried over from steward are **not** yet captured
> (deliberate follow-up, not oversight):
>
> - **No `culture.yaml`** (invisible to the detector): `tipalti`,
>   `cultureagent`, `cultureflare`, `irc-lens`, `agentirc`, `zehut`, `grant`
>   (renamed from `shushu`; the repo has no committed `culture.yaml` yet, so
>   `--scope mesh` cannot see it until one is added).
> - **Old skill-dir name** (`pr-review` / `coordinate`, which the detector
>   doesn't canonicalize): `daria`, `culture-sonar-cli` vendor `cicd`
>   under `pr-review`. `cfafi` / `culture` / `grant` are already listed with a
>   "still named `pr-review`/`coordinate`" note.
>
> `agentpypi` was **renamed to `auntiepypi`** on GitHub (the old name redirects);
> `auntiepypi` is the live consumer recorded above. Likewise `shushu` was
> **renamed to `grant`** on GitHub (the old name redirects); `grant` is the live
> consumer recorded above. guildmaster is bringing `grant` to the full canonical
> kit (`guild teach --all --to grant`); the remaining canonical skills register
> as downstream once `grant` applies the resync issue.

## Inbound workflow skills (origin = `devague`, re-broadcast by `guildmaster`)

These three flow the **opposite** direction of guildmaster's supplier role: a
sibling, [`devague`](https://github.com/agentculture/devague), is their
author/upstream; guildmaster pulls them from devague (formerly via steward) and
re-broadcasts them to the mesh. The `cite, don't import` rule still applies.
They are the `idea → spec → plan → implement` workflow operators that drive the
**deterministic** `devague` CLI (no LLM inside the CLI). Vendored at devague
`0.11.1` ([`c04b595`](https://github.com/agentculture/devague/commit/c04b595)),
**MIT**-licensed. Re-sync, when these later change upstream, from
`../devague/.claude/skills/<name>/`.

**Divergence from verbatim — `type: command` frontmatter.** devague's upstream
SKILL.md files carry only `name` + `description`. The copies here **add
`type: command`**: culture/agex's `core.skill_loader` requires `name`,
`description`, **and** `type:`, and a SKILL.md lacking `type:` is *silently
skipped* by `backends/claude_code/probe.py`. guildmaster declares an agent in
`culture.yaml`, so the addition is load-bearing on the culture backend and
harmless on `claude-code`. This is the only divergence from upstream.

| Skill | Origin | Downstream copies (known) | Notes |
|-------|--------|---------------------------|-------|
| `think` | `devague` (`agentculture/devague`, `../devague/.claude/skills/think/`) | — (broadcast pending), `agenda`, `dominion-breaker`, `convertible`, `jetson` | Operator for the **idea→spec** leg (announcement frame → capture/classify claims → interrogate with honesty conditions → park open vagueness → `export` once the frame converges). Renamed from `devague` in devague 0.4.0. **Divergence:** `type: command` added. Runtime dep: `uv tool install devague`. |
| `spec-to-plan` | `devague` (`agentculture/devague`, `../devague/.claude/skills/spec-to-plan/`) | — (broadcast pending), `agenda`, `dominion-breaker`, `convertible`, `jetson` | Operator for the **spec→plan** leg (`devague plan ...`): seed from a converged frame, cover every coverage target with acceptance-gated, acyclically-ordered tasks, park unknowns as risks, `export` once the plan converges. New in devague 0.4.0. **Divergence:** `type: command` added. Runtime dep: `uv tool install devague`. |
| `assign-to-workforce` | `devague` (`agentculture/devague`, `../devague/.claude/skills/assign-to-workforce/`) | — (broadcast pending), `agenda`, `dominion-breaker`, `convertible`, `jetson` | Operator for the **implementation** leg: reads `devague plan waves` (read-only) and fans out independent tasks to one agent per task per wave in isolated git worktrees, with main-agent TDD-gated merges. Three human gates: spec / split plan / final PR. The CLI stays non-orchestrating ([devague#20](https://github.com/agentculture/devague/issues/20)). New in devague 0.10.0. **Divergence:** `type: command` added. Runtime deps: `uv tool install devague`, `git worktree`, the vendored `cicd` skill (for gate-3 `agex pr open`). |

Downstream is empty by design: these are still being introduced to the mesh.
`guild teach --new --skill <name> --to <repos>` frames them as *new* skills to
add fresh (not stale copies to resync).

## guildmaster-origin skills (origin = `guildmaster`)

These are guildmaster's **own** operator skills — not vendored from anyone and
**not** part of the canonical set it supplies to siblings (so this table has no
Downstream column and the supplier surface does not track them). They are the
affordance + narration layer for guildmaster's own CLI surfaces.

| Skill | Origin | Notes |
|-------|--------|-------|
| `guild` | `guildmaster` (this repo) | Houses guildmaster's own read-only supplier surfaces. Today: `scripts/overview.sh`, the wrapper backing the pure-Python `guild overview` verb ([#12](https://github.com/agentculture/guildmaster/issues/12)) — the skills-supplier half of the inventory split, sibling to the vendored `agent-config` skill that backs `guild show`. Its `SKILL.md` is the skills-scoped excerpt of steward's `org-overview` narration contract (three layers: facts / inferred / suggestions; reflect-only). Surfaces skills/version drift that feeds `teach` / `onboard`; does NOT narrate steward's relationship graph or judge alignment. |
| `teach` | `guildmaster` (this repo) | Supplier broadcast verb: propagate a set of skills to a set of agents, one agent-major issue per target. Dry-run by default. |
| `onboard` | `guildmaster` (this repo) | Supplier ceremony verb: onboard a new sibling with the full canonical kit + identity + ledger registration. Dry-run by default. |

## Retained by `steward` (not guildmaster's to supply)

The cutover transferred only the **cross-sibling canonical set** above. These
steward skills stay with steward — they are steward-specific or otherwise not
part of guildmaster's supplied kit, and guildmaster does not broadcast them:

- `agent-config` (steward's **alignment-judgment** variant — distinct from
  guildmaster's inventory fork above; resolves Culture agent suffixes).
- `org-overview` — steward's reflect-only narration layer over `steward overview`;
  not portable without steward installed.
- `discord-notify` — generic webhook notifier; optional in the sibling baseline.
- `jekyll-test` — conditional; only meaningful for siblings shipping a Jekyll /
  Pages site.
- `notebooklm` — generates GitHub blob URLs for repo docs.

`cfafi`-origin skills (`cfafi`, `cfafi-write`, `poll`) remain with `cfafi`.

## Vendoring policy

- **Cite, don't import.** Skills are copied into the consuming repo, not
  symlinked or installed as a dependency. Each consumer owns and may modify
  their copy.
- **Re-sync explicitly.** When upstream changes, downstream copies do not
  auto-update; re-sync from the cited source and record the new pin here.
  `guild teach` / `guild onboard` are the broadcast paths that notify consumers.
- **Diverge intentionally.** A copy may diverge for repo-specific reasons
  (e.g. the `type: command` addition above, or `cfafi`'s CloudFlare-API
  reviewers in its `cicd`). Record the divergence here and in the skill's
  `SKILL.md` frontmatter `description`.

## When a skill should be promoted upstream

A skill currently owned downstream (e.g. `poll` in `cfafi`) should be promoted
to `guildmaster` when:

1. At least one other sibling has copy-pasted it, OR
2. Its scripts have no repo-specific assumptions (no hard-coded API credentials,
   no per-product paths), AND
3. Its `SKILL.md` describes a pattern (not a single product's workflow).

Promotion is a manual decision.
