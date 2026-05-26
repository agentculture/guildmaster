"""External-acts executor for ``guild create`` — template-instantiate approach.

Everything in :mod:`guild.scaffold.instantiate` is pure (no subprocess, no
network, no writes outside *dest*).  THIS module is the opposite half: given
the fully-parsed ``guild create`` arguments, :func:`apply` stands the repo up
by instantiating the GitHub template ``agentculture/culture-agent-template``
(or a caller-supplied override) and customising the clone.

Every external command is issued through an **injectable runner**, so the whole
executor is testable with a fake — no real GitHub, no real ``git``, and no
credentials required in tests/CI.

Sequence (``--apply``)
----------------------
0. ``gh auth status``                                (preflight: a gh login exists)
1. ``gh repo view <agent>``                          (preflight: repo must NOT exist)
2. ``gh repo create <agent>``                        (template instantiation)
   ``  --template <template>``
   ``  --public``
   ``  --description <desc>``
3. ``git clone https://github.com/<agent>.git <clone_dest>``
4. transform_clone(<clone_dest>, bare, desc, backend) (pure, local, no runner)
5. ``git -C <clone_dest> add -A``
6. ``git -C <clone_dest> commit -m "scaffold <bare> from culture-agent-template"``
7. ``git -C <clone_dest> push origin HEAD:main``    (genesis — BEFORE the branch lock)
8. ``bash .claude/skills/guild/scripts/configure-repo.sh <agent> --apply``
   (resolved from guildmaster's repo root; LAST, because its "Protect main"
   ruleset requires PRs and would otherwise reject the genesis push)

Preflight guard
---------------
:func:`preflight` refuses with NO partial work when:
- ``gh auth status`` fails (no gh login),
- ``gh repo view <agent>`` succeeds (repo already exists), or
- the local clone destination is already non-empty.

After a preflight failure the world is left exactly as found.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 — argv lists only; never shell=True
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.scaffold.instantiate import transform_clone

__all__ = [
    "apply",
    "preflight",
    "RunResult",
    "default_runner",
    "Runner",
    "CONFIGURE_REPO_SCRIPT",
]

# Resolve bash once at import time.
_BASH = shutil.which("bash") or "/bin/bash"

# Path to the configure-repo script, relative to the guildmaster repo root.
CONFIGURE_REPO_SCRIPT = ".claude/skills/guild/scripts/configure-repo.sh"

# Default template if the caller doesn't override.
DEFAULT_TEMPLATE = "agentculture/culture-agent-template"


# ---------------------------------------------------------------------------
# Runner seam
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """The shape every runner returns: a subset of ``CompletedProcess``."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


# A runner is anything callable as ``runner(cmd, cwd=None) -> RunResult``.
Runner = Callable[..., RunResult]


def default_runner(cmd: Sequence[str], *, cwd: str | None = None) -> RunResult:
    """Real runner: a thin wrapper over :func:`subprocess.run`.

    Always passed an argv **list** (never a string) and never ``shell=True`` —
    so there is no shell-injection surface.  ``check`` is intentionally False;
    callers inspect ``returncode`` and raise the typed :class:`GuildError`
    themselves.
    """
    proc = subprocess.run(  # nosec B603 — argv list, no shell
        list(cmd),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return RunResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_https_url(agent: str) -> str:
    """``agentculture/appsec`` -> ``https://github.com/agentculture/appsec.git``."""
    return f"https://github.com/{agent}.git"


def _dest_is_unusable(path: Path) -> bool:
    """True iff *path* exists as anything other than an empty directory.

    The clone destination must be absent or an empty dir. A file, symlink, or
    non-empty dir would otherwise pass the boundary guard and let ``apply``
    create the remote repo before ``git clone`` fails — a partial scaffold.
    """
    if not path.exists():
        return False
    if not path.is_dir():
        return True  # a file or symlink-to-file at the destination
    return any(path.iterdir())  # a non-empty directory


def _check(result: RunResult, message: str, code: int) -> None:
    """Raise a typed :class:`GuildError` if *result* indicates failure."""
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise GuildError(
            code=code,
            message=f"{message}: {detail}" if detail else message,
            remediation="check `gh`/`git` output above and your repo permissions",
        )


# ---------------------------------------------------------------------------
# Preflight — the boundary guard
# ---------------------------------------------------------------------------


def preflight(
    agent: str,
    clone_dest: Path,
    runner: Runner | None = None,
) -> None:
    """Refuse, with NO partial scaffold, unless the target is a clean new sibling.

    Checks, in order (short-circuits on first failure):

    1. **auth** — ``gh auth status`` must succeed.
    2. **existence** — ``gh repo view <agent>`` must FAIL (repo must not exist).
    3. **local boundary** — *clone_dest* must be absent or empty.

    Raises
    ------
    GuildError
        On any failed check.  Nothing external has been created or modified.
    """
    # Resolve the runner at call time so monkeypatching works in tests.
    if runner is None:
        runner = default_runner

    # 1. auth.
    auth = runner(["gh", "auth", "status"])
    if auth.returncode != 0:
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message="gh is not authenticated",
            remediation=(
                "run `gh auth login` (guildmaster reuses your gh login; no new tokens needed)"
            ),
        )

    # 2. existence — repo must NOT already exist.
    view = runner(["gh", "repo", "view", agent])
    if view.returncode == 0:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"repo {agent} already exists on GitHub",
            remediation=("choose a different --agent name, or delete the existing repo first"),
        )

    # 3. local boundary — the destination must be absent or an empty dir.
    #    A file/symlink/non-empty dir would clone-fail AFTER the remote exists.
    if _dest_is_unusable(clone_dest):
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"clone destination {clone_dest} must be absent or an empty directory",
            remediation=("remove it, empty the directory, or choose a different --workspace-root"),
        )


# ---------------------------------------------------------------------------
# Template-populate wait — gh copies the template asynchronously
# ---------------------------------------------------------------------------


def _wait_for_template(
    agent: str,
    runner: Runner,
    *,
    attempts: int = 30,
    delay: float = 2.0,
) -> None:
    """Block until GitHub has copied the template content into *agent*.

    ``gh repo create --template`` returns before the copy completes; the new
    repo is briefly empty (0 commits). Cloning then yields an empty tree and the
    transform runs on nothing. Poll the commit count until the template's
    initial commit lands.
    """
    for _ in range(max(1, attempts)):
        res = runner(["gh", "api", f"repos/{agent}/commits", "--jq", "length"])
        if res.returncode == 0 and res.stdout.strip().isdigit() and int(res.stdout.strip()) >= 1:
            return
        if delay:
            time.sleep(delay)
    raise GuildError(
        code=EXIT_ENV_ERROR,
        message=f"template content did not populate for {agent} within the timeout",
        remediation="GitHub's template copy is slow or failed — re-run `guild create`",
    )


# ---------------------------------------------------------------------------
# Apply — the external acts, in order
# ---------------------------------------------------------------------------


def apply(
    agent: str,
    bare: str,
    desc: str,
    backend: str,
    clone_dest: Path,
    guildmaster_root: Path,
    runner: Runner | None = None,
    template: str = DEFAULT_TEMPLATE,
    poll_attempts: int = 30,
    poll_delay: float = 2.0,
) -> dict:
    """Provision the new sibling repo by instantiating the template.

    Parameters
    ----------
    agent:
        Full ``owner/repo`` slug for the new repo.
    bare:
        The bare repo name (``repo`` part of the slug).
    desc:
        Short description embedded in the template and the ``gh repo create`` call.
    backend:
        ``"claude"`` or ``"acp"`` — controls the prompt file in the CLAUDE.md seed.
    clone_dest:
        Absolute path where the repo will be cloned locally.
    guildmaster_root:
        Root of the running guildmaster repo; used to resolve the configure-repo
        script path.
    runner:
        Callable ``(cmd, cwd=None) -> RunResult``.  Defaults to real subprocess.
    template:
        The GitHub template repo to instantiate (default: ``DEFAULT_TEMPLATE``).
    poll_attempts / poll_delay:
        ``gh repo create --template`` copies the template content
        **asynchronously**; cloning immediately yields an empty repo. After
        create, poll up to *poll_attempts* times (``poll_delay`` seconds apart)
        for the template's initial commit to land before cloning. Tests pass
        ``poll_delay=0``.

    Returns
    -------
    dict
        ``{"repo", "clone_dest", "pushed"}``.

    Raises
    ------
    GuildError
        On any preflight failure (no partial scaffold) or any external command
        failure.
    """
    # Resolve the runner at call time (not at import/definition time) so
    # monkeypatching ``_provision_template.default_runner`` works in tests.
    if runner is None:
        runner = default_runner

    # Boundary guard first.
    preflight(agent, clone_dest, runner=runner)

    # Step 2 — create the repo from the template.
    create = runner(
        [
            "gh",
            "repo",
            "create",
            agent,
            "--template",
            template,
            "--public",
            "--description",
            desc,
        ]
    )
    _check(create, f"gh repo create {agent} from template {template!r} failed", EXIT_ENV_ERROR)

    # Step 2b — wait for the async template copy to land (else the clone is empty).
    _wait_for_template(agent, runner, attempts=poll_attempts, delay=poll_delay)

    # Step 3 — clone.
    clone = runner(["git", "clone", _repo_https_url(agent), str(clone_dest)])
    _check(clone, f"git clone {agent} failed", EXIT_ENV_ERROR)

    # Step 4 — pure transform (no runner needed).
    transform_clone(clone_dest, bare, desc, backend)

    # Step 5 — stage everything.
    add = runner(["git", "-C", str(clone_dest), "add", "-A"])
    _check(add, "git add failed", EXIT_ENV_ERROR)

    # Step 6 — commit.
    commit = runner(
        [
            "git",
            "-C",
            str(clone_dest),
            "commit",
            "-m",
            f"scaffold {bare} from culture-agent-template",
        ]
    )
    _check(commit, "git commit (scaffold) failed", EXIT_ENV_ERROR)

    # Step 7 — push the genesis scaffold to main BEFORE the branch is locked.
    push = runner(["git", "-C", str(clone_dest), "push", "origin", "HEAD:main"])
    _check(push, "git push origin HEAD:main failed", EXIT_ENV_ERROR)

    # Step 8 — configure-repo.sh LAST: its "Protect main" ruleset requires PRs,
    # so applying it before the genesis push would get that push rejected.
    configure_script = guildmaster_root / CONFIGURE_REPO_SCRIPT
    if configure_script.is_file():
        cfg = runner([_BASH, str(configure_script), agent, "--apply"])
        _check(cfg, f"configure-repo.sh {agent} failed", EXIT_ENV_ERROR)

    return {
        "repo": agent,
        "clone_dest": str(clone_dest),
        "pushed": True,
    }
