"""``guild show`` — surface one agent's full configuration in a read-only view.

Wraps the vendored ``agent-config`` skill (``.claude/skills/agent-config/
scripts/show.sh``), which is the canonical implementation: it prints the
detected system-prompt file (``CLAUDE.md`` / ``AGENTS.md`` / ``GEMINI.md``), the
parallel ``culture.yaml``, and a one-line index of the agent's local skills.

This is guildmaster's **inventory** half of the steward → guildmaster split
(issue #12): it *reports* an agent's kit + config; it does not judge drift or
alignment (that stays with ``steward overview`` / ``steward doctor``). The CLI
is a thin typed surface — the same posture as steward's ``show`` — so operators
can run ``guild show ../culture`` instead of remembering the script path.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.cli._repo import find_git_root

# Resolve bash to an absolute path: show.sh uses bash arrays + `set -o pipefail`,
# so it must run under bash (not /bin/sh) and we never invoke a partial name.
_BASH = shutil.which("bash") or "/bin/bash"

_SKILL_SCRIPT = Path(".claude") / "skills" / "agent-config" / "scripts" / "show.sh"


def _resolve_skill_script() -> Path:
    """Locate the vendored ``show.sh`` inside the current git repo.

    Walks up from cwd but **stops at the git repository boundary** so ``guild
    show`` never executes a script from an ancestor directory outside the
    current checkout (search-path-injection guard). If cwd isn't inside any git
    repo, only cwd itself is inspected.
    """
    start = Path.cwd().resolve()
    repo_root = find_git_root(start)

    current = start
    while True:
        candidate = current / _SKILL_SCRIPT
        if candidate.is_file():
            return candidate
        if current == repo_root or current.parent == current:
            break
        if repo_root is None:
            # Not inside a git repo: inspect cwd only, never ancestors.
            break
        current = current.parent

    raise GuildError(
        code=EXIT_ENV_ERROR,
        message="agent-config skill script not found",
        remediation=(
            "run from inside a guildmaster checkout that vendors "
            ".claude/skills/agent-config/scripts/show.sh"
        ),
    )


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "show",
        help="Show one agent's full configuration (prompt file + culture.yaml + skills).",
        description=(
            "Surface a Culture agent's detected system-prompt file, its parallel "
            "culture.yaml, and its .claude/skills index in one read-only view. "
            "Accepts a directory path or a registered agent suffix. Wraps the "
            "vendored agent-config skill; inventory only, no drift verdict."
        ),
    )
    parser.add_argument(
        "target",
        help="Path to a project directory, or a registered agent suffix.",
    )
    parser.set_defaults(func=_handle)


def _handle(args: argparse.Namespace) -> int:
    script = _resolve_skill_script()
    # Forward stdout/stderr via Python streams so the stdout (result) / stderr
    # (diagnostics) split is preserved and pytest's capsys sees the output.
    #
    # bandit S603: argv is a fixed list — bash + the repo-resolved script path +
    # the positional target string (no shell, no expansion). _resolve_skill_script
    # constrains the script to the current git repo, so an ancestor directory
    # cannot substitute a different show.sh.
    try:
        completed = subprocess.run(  # noqa: S603
            [_BASH, str(script), args.target],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message=f"could not execute {script}: {exc}",
            remediation="ensure bash is installed and the script is present",
        ) from exc

    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)

    if completed.returncode != 0:
        # show.sh exits 2 for user errors (no/unknown target) and 1 for env
        # errors (missing manifest / PyYAML). Mirror that split.
        raise GuildError(
            code=EXIT_USER_ERROR if completed.returncode == 2 else EXIT_ENV_ERROR,
            message=f"agent-config script exited {completed.returncode}",
            remediation=f"see stderr from {script.name}",
        )
    return 0
