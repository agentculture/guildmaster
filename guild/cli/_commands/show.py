"""``guild show`` — surface one agent's full configuration in a read-only view.

Reports an agent's three config artifacts together: the detected system-prompt
file (``CLAUDE.md`` / ``AGENTS.md`` / ``GEMINI.md``), the parallel
``culture.yaml``, and a one-line index of the agent's local skills.

This is guildmaster's **inventory** half of the steward → guildmaster split
(issue #12): it *reports* an agent's kit + config; it does not judge drift or
alignment (that stays with ``steward overview`` / ``steward doctor``).

Resolution (path → directory, or registered suffix → directory via the Culture
server manifest) happens **once, in Python**, so both output modes agree:

* default — shell out to the vendored ``agent-config`` ``show.sh`` (the canonical
  human renderer, cite-don't-import from steward) in path mode on the resolved
  directory;
* ``--json`` — build a structured object natively from the same three artifacts
  (data-producing verbs must offer ``--json``, like every other ``guild`` verb).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.cli._output import emit_result
from guild.cli._repo import find_git_root, iter_skills, load_culture_yaml

# Resolve bash to an absolute path: show.sh uses bash arrays + `set -o pipefail`,
# so it must run under bash (not /bin/sh) and we never invoke a partial name.
_BASH = shutil.which("bash") or "/bin/bash"

_DOT_CLAUDE = ".claude"
_SKILL_REL = Path(_DOT_CLAUDE) / "skills" / "agent-config"
_LOCAL_CFG = Path(_DOT_CLAUDE) / "skills.local.yaml"
_LOCAL_CFG_EXAMPLE = Path(_DOT_CLAUDE) / "skills.local.yaml.example"
# Fallback prompt filenames when the backend-fingerprint registry is absent.
_PROMPT_FALLBACK = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def _find_skill_dir() -> Path | None:
    """Locate the vendored ``agent-config`` skill dir inside the current git repo.

    Walks up from cwd but **stops at the git repository boundary** so ``guild
    show`` never executes a script from an ancestor directory outside the
    current checkout (search-path-injection guard). Returns ``None`` when the
    skill isn't vendored.
    """
    start = Path.cwd().resolve()
    repo_root = find_git_root(start)
    current = start
    while True:
        candidate = current / _SKILL_REL
        if (candidate / "scripts" / "show.sh").is_file():
            return candidate
        if current == repo_root or current.parent == current or repo_root is None:
            break
        current = current.parent
    return None


def _read_local_config(repo_root: Path | None) -> dict[str, Any]:
    """Read ``.claude/skills.local.yaml`` (falling back to the committed
    ``.example``) from the repo root, as a dict. Empty when neither exists."""
    if repo_root is None:
        return {}
    for name in (_LOCAL_CFG, _LOCAL_CFG_EXAMPLE):
        path = repo_root / name
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    return {}


def _resolve_target_dir(target: str, repo_root: Path | None) -> Path:
    """Resolve *target* to an existing directory.

    Path mode: *target* is a directory (inspected as-is — cross-repo inventory
    such as ``guild show ../culture`` is the point). Otherwise, suffix mode
    resolves a registered agent suffix via the Culture server manifest.
    """
    path = Path(target).expanduser()
    if path.is_dir():
        return path
    return _resolve_suffix(target, repo_root)


def _manifest_path(target: str, repo_root: Path | None) -> Path:
    """The Culture server manifest named by ``culture_server_yaml`` in
    ``.claude/skills.local.yaml``. Raises an env error if unset or absent."""
    server_yaml = _read_local_config(repo_root).get("culture_server_yaml")
    if not server_yaml:
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message=f"{target!r} is not a directory and no culture_server_yaml is configured",
            remediation=f"pass a directory path, or set culture_server_yaml in {_LOCAL_CFG}",
        )
    manifest = Path(str(server_yaml)).expanduser()
    if not manifest.is_file():
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message=f"no server manifest at {manifest}",
            remediation=f"set culture_server_yaml in {_LOCAL_CFG}, or pass a directory path",
        )
    return manifest


def _resolve_suffix(target: str, repo_root: Path | None) -> Path:
    """Resolve a registered agent *suffix* to its checkout directory."""
    manifest = _manifest_path(target, repo_root)
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    entry = (data.get("agents") or {}).get(target)
    if entry is None:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"no agent registered with suffix {target!r} in {manifest}",
            remediation="pass a directory path or a registered agent suffix",
        )
    directory = entry.get("directory") if isinstance(entry, dict) else entry
    resolved = Path(str(directory)).expanduser()
    if not resolved.is_dir():
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"agent {target!r} resolves to {resolved}, which is not a directory",
            remediation="check the server manifest entry, or pass a directory path",
        )
    return resolved


def _prompt_filenames(skill_dir: Path | None) -> list[str]:
    """Recognized prompt filenames, from the vendored backend-fingerprint
    registry (shared source of truth with ``show.sh``), else the built-in list."""
    if skill_dir is not None:
        registry = skill_dir / "data" / "backend-fingerprints.yaml"
        if registry.is_file():
            data = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
            names: list[str] = []
            for spec in (data.get("backends") or {}).values():
                prompt = spec.get("prompt") if isinstance(spec, dict) else None
                if prompt and prompt not in names:
                    names.append(prompt)
            if names:
                return sorted(names)
    return list(_PROMPT_FALLBACK)


def _build_json(target: str, directory: Path, skill_dir: Path | None) -> dict[str, Any]:
    """Build the structured config view: detected prompt file (+ contents),
    parsed ``culture.yaml`` (or ``None``), and the local skills index."""
    detected: str | None = None
    prompt_text: str | None = None
    for name in _prompt_filenames(skill_dir):
        candidate = directory / name
        if candidate.is_file():
            detected = name
            prompt_text = candidate.read_text(encoding="utf-8")
            break
    return {
        "target": target,
        "dir": str(directory),
        "prompt_file": detected,
        "prompt": prompt_text,
        "culture_yaml": load_culture_yaml(directory),
        "skills": [{"name": s.name, "description": s.description} for s in iter_skills(directory)],
    }


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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the config as a JSON object to stdout instead of the rendered view.",
    )
    parser.set_defaults(func=_handle)


def _run_show_script(script: Path, directory: Path) -> int:
    """Render the human view by shelling out to the vendored show.sh (path mode).

    bandit S603: argv is a fixed list — bash + the repo-resolved script path + a
    Python-resolved directory (no shell, no expansion). The script is constrained
    to the current git repo, so an ancestor directory cannot substitute a
    different show.sh.
    """
    try:
        completed = subprocess.run(  # noqa: S603
            [_BASH, str(script), str(directory)],
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
    if completed.returncode != 0:
        # Route the script's own diagnostic through GuildError so failure output
        # stays the structured `error:` / `hint:` shape (no raw, duplicated stderr).
        detail = completed.stderr.strip() or f"agent-config script exited {completed.returncode}"
        raise GuildError(
            code=EXIT_USER_ERROR if completed.returncode == 2 else EXIT_ENV_ERROR,
            message=detail,
            remediation="pass a directory path or a registered agent suffix",
        )
    if completed.stderr:
        # Non-fatal diagnostics from the script (rare on a resolved path).
        sys.stderr.write(completed.stderr)
    return 0


def _handle(args: argparse.Namespace) -> int:
    repo_root = find_git_root(Path.cwd().resolve())
    skill_dir = _find_skill_dir()

    # Human mode needs the vendored renderer; fail fast and clearly if it's absent.
    if not args.json and skill_dir is None:
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message="agent-config skill script not found",
            remediation=(
                "run from inside a guildmaster checkout that vendors "
                ".claude/skills/agent-config/scripts/show.sh"
            ),
        )

    directory = _resolve_target_dir(args.target, repo_root)

    if args.json:
        emit_result(json.dumps(_build_json(args.target, directory, skill_dir), indent=2))
        return 0

    assert skill_dir is not None  # guaranteed by the guard above
    return _run_show_script(skill_dir / "scripts" / "show.sh", directory)
