#!/usr/bin/env bash
# onboard — forward to `guild onboard`, resolving the CLI portably.
#
# Prefers an installed `guild` on PATH (the normal case), falling back to
# `uv run guild` inside a source checkout. Every argument is forwarded verbatim.
# Dry-run is the CLI's default; pass --apply to file the issue + write the
# ledger + record the pins.
set -euo pipefail

if command -v guild >/dev/null 2>&1; then
    exec guild onboard "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run guild onboard "$@"
fi

echo "guild not found on PATH. Install it: uv tool install guild-cli" >&2
exit 2
