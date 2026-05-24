#!/usr/bin/env bash
# teach — forward to `guild teach`, resolving the CLI portably.
#
# Prefers an installed `guild` on PATH (the normal case), falling back to
# `uv run guild` inside a source checkout. Every argument is forwarded verbatim,
# so this wrapper exists only for portable resolution + discoverability as a
# skill. Dry-run is the CLI's default; pass --apply to file issues.
set -euo pipefail

if command -v guild >/dev/null 2>&1; then
    exec guild teach "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run guild teach "$@"
fi

echo "guild not found on PATH. Install it: uv tool install guild-cli" >&2
exit 2
