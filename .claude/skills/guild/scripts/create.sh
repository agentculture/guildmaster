#!/usr/bin/env bash
set -euo pipefail
# create — invoke `guild create` from guildmaster's repo root.
#
# Instantiates agentculture/culture-agent-template (or a caller-supplied
# --template) for a new sibling agent, renames identifiers, writes a self-init
# CLAUDE.md seed, configures the GitHub repo, pushes the genesis commit, and
# registers the agent in docs/skill-sources.md.
#
# Dry-run by default; --apply executes.
#
# Usage:
#   create.sh --agent OWNER/REPO --desc TEXT [--backend claude|acp]
#             [--workspace-root DIR] [--template OWNER/REPO]
#             [--org agentculture] [--command NAME] [--pkg NAME]
#             [--dist NAME] [--apply] [--json]
#
# The repo name is the repo/agent identity (README, culture.yaml suffix,
# CLAUDE.md seed, repo URL). --command / --pkg / --dist each retarget one facet
# independently and default to the repo name (or, for --pkg, the underscore form
# of --command), so with no overrides the result is identical to before:
#   --command NAME  console-command name (the [project.scripts] key only); e.g.
#                   --command reachy for a repo reachy-mini-cli.
#   --pkg NAME      importable package; defaults to the underscore form of
#                   --command (pass only to decouple command from package).
#   --dist NAME     PyPI distribution name; e.g. --dist jetson-cli. Retargets
#                   [project].name, the importlib.metadata lookup, and the
#                   TestPyPI install pin.
#
# Exit codes:
#   0   success (delegates to `guild create`; its exit code propagates)
#   1   environment error (no way to invoke guild)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve guildmaster's repo root.
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
fi
cd "$REPO_ROOT"

# Resolve how to invoke guild.
if command -v guild >/dev/null 2>&1; then
    GUILD=(guild)
elif [ -f "$REPO_ROOT/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
    GUILD=(uv run --project "$REPO_ROOT" guild)
elif command -v python3 >/dev/null 2>&1; then
    GUILD=(python3 -m guild)
else
    echo "create: cannot invoke guild (need 'guild', 'uv', or 'python3' on PATH)" >&2
    exit 1
fi

exec "${GUILD[@]}" create "$@"
