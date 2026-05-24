#!/usr/bin/env bash
set -euo pipefail
# overview — assemble the `guild overview` skills-supplier evidence pack for
# narration.
#
# The guildmaster agent runs this, then narrates the supplier view (the
# canonical skill set + versions/origins, the docs/skill-sources.md ledger, and
# the drift signals that feed `teach` / `onboard`). See SKILL.md.
# Deterministic glue only: resolve guildmaster's repo root, run from there,
# resolve how to invoke guild, pick the scope, and delegate to `guild overview`.
# No interpretation.
#
# Usage:
#   overview.sh                  # whole ledger across the mesh (--scope all)
#   overview.sh <agent>          # one agent's kit + gaps       (--scope self)
#   overview.sh --scope mesh     # live filesystem survey of every agent
#   overview.sh --json           # all, JSON evidence
#   overview.sh <agent> --json   # one agent, JSON evidence
#
# Contract: the FIRST argument, if it does not start with '-', is the agent
# (self scope). All remaining arguments pass through to `guild overview`.
#
# Exit codes:
#   0   success (delegates to `guild overview`; its exit code propagates)
#   1   environment error (no way to invoke guild)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve guildmaster's repo root and run from there, so `guild overview` always
# reports guildmaster's canonical set regardless of the caller's working
# directory (the CLI reads its repo from cwd). Prefer git (robust); fall back to
# climbing out of the fixed .claude/skills/<name>/scripts/ layout when git is
# unavailable.
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
    echo "overview: cannot invoke guild (need 'guild', 'uv', or 'python3' on PATH)" >&2
    exit 1
fi

# Honor an explicit --scope passed through (advanced use); otherwise pick one.
has_scope=false
for arg in "$@"; do
    case "$arg" in
        --scope | --scope=*)
            has_scope=true
            break
            ;;
    esac
done

overview_args=()
if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
    # First arg is an agent → one-agent (self) scope.
    agent="$1"
    shift
    $has_scope || overview_args+=(--scope self)
    overview_args+=("$agent")
else
    # No leading agent → whole-ledger (all) view.
    $has_scope || overview_args+=(--scope all)
fi
overview_args+=("$@")

exec "${GUILD[@]}" overview "${overview_args[@]}"
