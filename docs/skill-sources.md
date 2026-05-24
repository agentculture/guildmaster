# Skill sources — guildmaster's vendored skills

guildmaster currently vendors skills as a **consumer**. Per the settled
division of labor ([issue #1](https://github.com/agentculture/guildmaster/issues/1)),
guildmaster becomes the skills **supplier/manager** for the AgentCulture mesh —
but it onboards as a consumer first, vendoring the canonical skill set like every
other sibling before taking over the upstream ledger, the
`announce-skill-update` broadcast, and skill-version tracking. Until that
ownership transfers, `steward` holds the live supplier ledger
(`../steward/docs/skill-sources.md`) and this file records only what guildmaster
itself vendors.

Everything here follows **cite, don't import**: each skill is *copied* into
`.claude/skills/<name>/`, not symlinked or installed as a cross-repo dependency.
guildmaster owns its copy and may diverge from upstream; nothing reaches across
skill boundaries at runtime. When upstream changes, downstream copies do **not**
auto-update — re-sync explicitly from the cited source.

## Consumed canonical skills (upstream = `steward`)

These flow from `steward`, the mesh's current skill supplier. guildmaster
vendored them during its initial scaffold
([issue #1](https://github.com/agentculture/guildmaster/issues/1)). Re-sync from
`../steward/.claude/skills/<name>/`.

| Skill | Upstream | Notes |
|-------|----------|-------|
| `cicd` | `steward` (`../steward/.claude/skills/cicd/`) | PR lifecycle; thin delegate layered on `agex pr` with guildmaster's `status` / `await` extensions. |
| `communicate` | `steward` (`../steward/.claude/skills/communicate/`) | Cross-repo issue I/O + mesh messaging. Broadcast templates repointed from steward to guildmaster as the future supplier. |
| `version-bump` | `steward` (`../steward/.claude/skills/version-bump/`) | Pure-Python semver bump + Keep-a-Changelog entry; no per-repo customization. |
| `run-tests` | `steward` (`../steward/.claude/skills/run-tests/`) | pytest with parallelism + coverage; coverage source resolves from `pyproject.toml`. |
| `sonarclaude` | `steward` (`../steward/.claude/skills/sonarclaude/`) | SonarCloud API client; project key from `$SONAR_PROJECT` or `--project`. |
| `doc-test-alignment` | `steward` (`../steward/.claude/skills/doc-test-alignment/`) | Stub today; real implementation TBD upstream. |
| `pypi-maintainer` | `steward` (`../steward/.claude/skills/pypi-maintainer/`) | Switches a PyPI install between pypi / test-pypi / local. |
| `agent-config` | `steward` (`../steward/.claude/skills/agent-config/`) | Per-agent config view backing `guild show` ([#12](https://github.com/agentculture/guildmaster/issues/12)); `show.sh` + `data/backend-fingerprints.yaml` are vendored verbatim. **Divergence:** SKILL.md reframed from steward's alignment-judgment framing to guildmaster's inventory role and adds `type: command` for the culture backend's skill loader. |

## Inbound workflow skills (origin = `devague`, re-broadcast via `steward`)

These three flow the **opposite** direction of guildmaster's supplier role: a
sibling, [`devague`](https://github.com/agentculture/devague), is their
author/upstream; `steward` pulls them from devague and re-broadcasts them to the
mesh; guildmaster vendors its copy from steward's. They are the
`idea → spec → plan → implement` workflow operators that drive the
**deterministic** `devague` CLI (no LLM inside the CLI). Vendored from steward's
copy at commit
[`914d5ca`](https://github.com/agentculture/steward/commit/914d5ca), which
tracks devague `0.11.1`
([`c04b595`](https://github.com/agentculture/devague/commit/c04b595)),
**MIT**-licensed. Resolves guildmaster issues
[#5](https://github.com/agentculture/guildmaster/issues/5),
[#6](https://github.com/agentculture/guildmaster/issues/6), and
[#7](https://github.com/agentculture/guildmaster/issues/7). Re-sync, when these
later change upstream, from `../steward/.claude/skills/<name>/` (which tracks
`../devague/.claude/skills/<name>/`).

**Divergence from verbatim — `type: command` frontmatter.** devague's upstream
SKILL.md files carry only `name` + `description`. The copies here (taken from
steward) **add `type: command`**: culture/agex's `core.skill_loader` requires
`name`, `description`, **and** `type:`, and a SKILL.md lacking `type:` is
*silently skipped* by `backends/claude_code/probe.py`. guildmaster declares an
agent in `culture.yaml`, so the addition is load-bearing on the culture backend
and harmless on `claude-code`. This is the only divergence from upstream.

| Skill | Origin | Notes |
|-------|--------|-------|
| `think` | `devague` (`agentculture/devague`, `../devague/.claude/skills/think/`) | Operator for the **idea→spec** leg (working backwards: announcement frame → capture/classify claims → interrogate with honesty conditions → park open vagueness → `export` once the frame converges). Renamed from `devague` in devague 0.4.0. **Divergence:** `type: command` added. Runtime dep: `uv tool install devague`. |
| `spec-to-plan` | `devague` (`agentculture/devague`, `../devague/.claude/skills/spec-to-plan/`) | Operator for the **spec→plan** leg (`devague plan ...`): seed from a converged frame, cover every coverage target with acceptance-gated, acyclically-ordered tasks, park unknowns as risks, `export` once the plan converges. New in devague 0.4.0. **Divergence:** `type: command` added. Runtime dep: `uv tool install devague`. |
| `assign-to-workforce` | `devague` (`agentculture/devague`, `../devague/.claude/skills/assign-to-workforce/`) | Operator for the **implementation** leg: reads `devague plan waves` (read-only) and fans out independent tasks to one agent per task per wave in isolated git worktrees, with main-agent TDD-gated merges. Three human gates: spec / split plan / final PR. The CLI stays non-orchestrating ([devague#20](https://github.com/agentculture/devague/issues/20)). New in devague 0.10.0. **Divergence:** `type: command` added. Runtime deps: `uv tool install devague`, `git worktree`, the vendored `cicd` skill (for the gate-3 `agex pr open`). |

## Vendoring policy

- **Cite, don't import.** Skills are copied into this repo, not symlinked or
  installed as a dependency. guildmaster owns and may modify each copy.
- **Re-sync explicitly.** When upstream changes, this copy does not auto-update;
  re-sync from the cited source and record the new pin here.
- **Diverge intentionally.** A copy may diverge for repo-specific reasons
  (e.g. the `type: command` addition above). Record the divergence here and in
  the skill's `SKILL.md` frontmatter `description`.
