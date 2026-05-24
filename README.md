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
