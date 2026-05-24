# guildmaster

**An agent and CLI that manages skills** for the
[AgentCulture](https://github.com/agentculture) mesh.

guildmaster is a sibling to [`steward`](https://github.com/agentculture/steward)
(resident-agent alignment), [`culture`](https://github.com/agentculture/culture)
(the IRC-based agent mesh), and [`daria`](https://github.com/agentculture/daria)
(the awareness agent) in the Organic Development framework. Its mission is skill
and skillversion management plus an overview surface for the mesh: per the
settled division of labor ([issue #1](https://github.com/agentculture/guildmaster/issues/1)),
guildmaster becomes the skills **supplier/manager** while steward retreats to
agent-alignment. It onboards as a **consumer** first — vendoring the canonical
skills like every other sibling — before taking over the upstream ledger,
broadcast, and version tracking.

The repo and the Culture agent are named `guildmaster`; the CLI ships as
`guild-cli` on PyPI and installs the `guild` binary.

## Install

```bash
# From PyPI (Trusted Publishing):
uv tool install guild-cli

# From source (dev):
uv sync
uv run guild --version
```

## Commands

All verbs are read-only, offline, and deterministic — safe to call in agent
loops. Add `--json` to any of them for structured output.

| Verb | What it does |
|------|--------------|
| `guild whoami` | Report this agent's identity — suffix + backend (from `culture.yaml`) + version. The smallest identity probe. |
| `guild learn` | Survey the repo: the CLI verbs, the vendored skills under `.claude/skills/`, and a pointer to `CLAUDE.md`. |
| `guild explain <topic>` | Explain one topic in depth — print a vendored skill's `SKILL.md`, or a verb's summary. |

```bash
uv run guild whoami
uv run guild learn
uv run guild explain cicd
```

### Supplier verbs — `teach` & `onboard`

As the mesh's skills supplier, guildmaster propagates skills to sibling agents
through two **agent-first write** verbs. Both default to **dry-run** (render the
issues and the ledger/verification diffs); `--apply` files them.

| Verb | What it does |
|------|--------------|
| `guild teach --skill <name> … --to <agent> …` | Teach a chosen **set** of skills to a chosen **set** of mesh agents. |
| `guild onboard --agent <owner/repo>` | Welcome a **brand-new** sibling with the full canonical kit, an identity-setup section, ledger registration, and a verification record. |

**Agent-major, not skill-major.** A run files **one GitHub issue per target
agent**, bundling a per-skill *section* for every skill that agent receives —
not one issue per skill. New-vs-resync framing is auto-detected per
`(skill, agent)` from the `docs/skill-sources.md` ledger. Skills must be chosen
explicitly (`--skill`, repeatable, or `--all`) — there is no implicit default.

**These supersede a separate `announce-skill-update` verb.** `teach` is the
single render-and-post engine; `onboard` is "`teach` the whole canonical kit"
plus ledger registration, the identity section, and a verification record. There
is no standalone broadcast verb (cf.
[issue #10](https://github.com/agentculture/guildmaster/issues/10), which asked
for one — guildmaster fulfills the broadcast *role* via these two verbs instead).

**Before → after.** Today guildmaster has no broadcast verb of its own —
`steward` runs the live broadcaster, and teaching a set of skills or standing up
a new sibling is manual (hand-rendered briefs, hand-edited ledger, no
verification). After: **one command** propagates a skill set, or onboards a
sibling end-to-end. Going live is gated on the staged steward→guildmaster
cutover — see [`docs/cutover.md`](docs/cutover.md).

## Develop

```bash
uv sync
uv run pytest -n auto -v
uv run black --check guild tests && uv run isort --check-only guild tests
uv run flake8 guild tests && uv run bandit -c pyproject.toml -r guild
```

Every PR bumps the version (CI's `version-check` enforces it):

```bash
python3 .claude/skills/version-bump/scripts/bump.py patch
```

See [`CLAUDE.md`](CLAUDE.md) for the full project shape, conventions, and the
build/test/publish toolchain.
