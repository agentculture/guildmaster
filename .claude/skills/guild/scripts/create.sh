#!/usr/bin/env bash
set -euo pipefail
# create — provision a brand-new AgentCulture sibling repo end-to-end.
#
# The guildmaster agent runs this to stand up a new sibling from one request:
# it builds a dry-run ProvisionPlan by default, or (with --apply) creates the
# public MIT GitHub repo, clones it into the workspace, vendors the canonical
# skill kit + identity, pushes the genesis commit to main, and registers the
# agent in docs/skill-sources.md. See SKILL.md.
# Deterministic glue only: resolve guildmaster's repo root, run from there,
# resolve how to invoke guild, and delegate to `guild create`. No interpretation.
#
# Usage:
#   create.sh --agent <owner/repo> --desc "<description>"            # dry-run
#   create.sh --agent <owner/repo> --desc "..." --apply             # execute
#   create.sh --agent <owner/repo> --desc "..." --json              # JSON plan
#   create.sh --agent <owner/repo> --desc "..." --backend acp       # acp prompt
#
# Contract: all arguments pass through verbatim to `guild create`.
#
# Exit codes:
#   0   success (delegates to `guild create`; its exit code propagates)
#   1   environment error (no way to invoke guild)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve guildmaster's repo root and run from there, so `guild create` always
# reads guildmaster's canonical kit + ledger regardless of the caller's working
# directory. Prefer git (robust); fall back to climbing out of the fixed
# .claude/skills/<name>/scripts/ layout when git is unavailable.
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
fi
cd "$REPO_ROOT"

# Resolve how to invoke guild: installed console script, then uv, then module.
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
