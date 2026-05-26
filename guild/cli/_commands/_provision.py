"""External-acts executor for ``guild create`` — the ``--apply`` side (t6).

Everything in :mod:`guild.scaffold.plan` is pure (no subprocess, no network, no
writes). THIS module is the opposite half: given a fully-composed
:class:`~guild.scaffold.plan.ProvisionPlan`, :func:`apply` actually stands the
repo up. Every external command is issued through an **injectable runner**, so
the whole executor is testable with a fake — no real GitHub, no real ``git``,
and (resolving plan risk *r2*) **no credentials required in tests/CI**.

Risk r1 resolution — "push the genesis commit to main" stays literally true
-----------------------------------------------------------------------------
``gh repo create X --license mit`` would seed an *initial* commit (a LICENSE)
on the new repo, which would collide with pushing our own genesis commit to
``main``. We therefore create an **empty** repo — ``gh repo create <agent>
--public --description <desc>`` with **no** ``--license`` and **no**
``--gitignore`` — so GitHub adds no competing initial commit. The scaffold
manifest from t1 already contains an MIT ``LICENSE`` file, so GitHub
auto-detects the MIT license from that file once it is pushed. The chosen,
strictly-ordered sequence is:

    0. gh auth status                         # preflight: a gh login exists
    1. gh repo view <agent>                   # preflight: must NOT exist yet
    2. gh repo create <agent> --public \\
         --description <desc>                  # empty repo, NO --license
    3. git clone <https-url> <clone_dest>     # clone the empty repo
    4. <write manifest + copy kit into clone_dest>
    5. git -C <clone_dest> add -A
    6. git -C <clone_dest> commit -m <genesis msg>   # THE genesis commit
    7. git -C <clone_dest> branch -M main            # ensure branch is 'main'
    8. git -C <clone_dest> push -u origin main       # push genesis to main

Boundary guard (covers c6 / h10) — :func:`preflight` refuses with NO partial
scaffold when the GitHub repo already exists, when ``gh`` auth is missing, or
when the local clone destination already exists and is **non-empty**. We never
scaffold arbitrary content into a target that is outside the clean
"new empty sibling" shape.

Credentials — we use ONLY the ``gh`` login guildmaster already holds (the same
auth surface :mod:`guild.cli._commands._broadcast` relies on for posting
issues). No new tokens, no new auth surface.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - argv lists only; never shell=True
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from guild.cli._errors import EXIT_ENV_ERROR, EXIT_USER_ERROR, GuildError
from guild.scaffold.kit import copy_plan as _copy_plan
from guild.scaffold.plan import ProvisionPlan

__all__ = ["apply", "preflight", "RunResult", "default_runner", "Runner"]


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
    so there is no shell-injection surface (keeps ``bandit`` quiet). ``check``
    is intentionally False; callers inspect ``returncode`` and raise the typed
    :class:`GuildError` themselves so every failure carries a remediation hint.
    """
    proc = subprocess.run(  # nosec B603 - argv list, no shell
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


def _dir_is_nonempty(path: Path) -> bool:
    """True iff *path* exists, is a directory, and contains at least one entry."""
    return path.is_dir() and any(path.iterdir())


def _genesis_message(agent: str, desc: str) -> str:
    bare = agent.rsplit("/", 1)[-1]
    return f"chore: scaffold {bare} from guildmaster\n\n{desc}"


# ---------------------------------------------------------------------------
# Preflight — the boundary guard (raises BEFORE anything is created)
# ---------------------------------------------------------------------------


def preflight(plan: ProvisionPlan, runner: Runner = default_runner) -> None:
    """Refuse, with NO partial scaffold, unless the target is a clean new sibling.

    Performs, in order and short-circuiting on the first failure:

    1. **auth** — ``gh auth status`` must be zero, else
       :class:`GuildError` (:data:`EXIT_ENV_ERROR`). We use only the ``gh``
       login guildmaster already holds; this is the no-new-auth-surface check.
    2. **existence** — ``gh repo view <agent>`` must be **nonzero** (repo
       absent). If it is zero the repo exists -> :class:`GuildError`
       (:data:`EXIT_USER_ERROR`); nothing else runs, nothing is created.
    3. **local boundary** — the clone destination must not already exist with
       content. A non-empty dest -> :class:`GuildError` (:data:`EXIT_USER_ERROR`)
       so we never scaffold over arbitrary existing files (c6/h10). An empty or
       absent dest is fine.

    Because this runs *before* any create/clone/write, a failure here leaves the
    world exactly as it was found.
    """
    agent = plan.repo_spec["agent"]

    # 1. auth — only the existing gh login.
    auth = runner(["gh", "auth", "status"])
    if auth.returncode != 0:
        raise GuildError(
            code=EXIT_ENV_ERROR,
            message="gh is not authenticated",
            remediation="run `gh auth login` (guildmaster reuses your gh login; no new tokens)",
        )

    # 2. existence — the repo must NOT already exist.
    view = runner(["gh", "repo", "view", agent])
    if view.returncode == 0:
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"repo {agent} already exists on GitHub",
            remediation="choose a different --agent name, or delete the existing repo first",
        )

    # 3. local boundary — never clobber a non-empty destination.
    clone_dest = Path(plan.repo_spec["clone_dest"])
    if _dir_is_nonempty(clone_dest):
        raise GuildError(
            code=EXIT_USER_ERROR,
            message=f"clone destination {clone_dest} already exists and is non-empty",
            remediation="remove or empty the directory, or pick a different workspace root",
        )


# ---------------------------------------------------------------------------
# Apply — the external acts, in order
# ---------------------------------------------------------------------------


def apply(
    plan: ProvisionPlan,
    runner: Runner = default_runner,
    *,
    kit_src: dict[str, str] | None = None,
    root: Path | None = None,
) -> dict:
    """Provision the new sibling repo described by *plan*.

    Steps (see the module docstring for the full rationale + r1 resolution):
    preflight -> ``gh repo create`` (empty, public, with description) ->
    ``git clone`` -> write manifest + copy kit -> ``git add -A`` ->
    ``git commit`` (genesis) -> ``git branch -M main`` -> ``git push -u origin
    main``.

    Parameters
    ----------
    plan:
        The fully-composed :class:`ProvisionPlan` from
        :func:`guild.scaffold.plan.build`.
    runner:
        The external-command seam. Defaults to :func:`default_runner` (real
        subprocess); tests inject a fake. Called as ``runner(cmd, cwd=...)``.
    kit_src:
        Optional ``dest-relpath -> abs-source-path`` map for the canonical kit.
        When omitted it is reconstructed from
        :func:`guild.scaffold.kit.copy_plan` against *root* (this is the normal
        path); tests pass it explicitly to stay independent of guildmaster's own
        ``.claude/skills``.
    root:
        guildmaster repo root used to reconstruct *kit_src* when it is not
        supplied. Resolved via :func:`guild.cli._repo.repo_root` when ``None``.

    Returns
    -------
    dict
        Result summary: ``{"repo", "clone_dest", "manifest_files", "kit_files",
        "pushed", "applied"}``.

    Raises
    ------
    GuildError
        On any preflight failure (no partial scaffold) or any external command
        failure (with a remediation hint).
    """
    # Boundary guard first — fail fast, leave the world untouched.
    preflight(plan, runner=runner)

    agent = plan.repo_spec["agent"]
    desc = plan.repo_spec["desc"]
    clone_dest = Path(plan.repo_spec["clone_dest"])

    # --- 1. Create the EMPTY repo (r1: no --license / --gitignore) -----------
    create = runner(
        [
            "gh",
            "repo",
            "create",
            agent,
            "--public",
            "--description",
            desc,
        ]
    )
    _check(create, f"gh repo create {agent} failed", EXIT_ENV_ERROR)

    # --- 2. Clone the empty repo into the workspace --------------------------
    clone = runner(["git", "clone", _repo_https_url(agent), str(clone_dest)])
    _check(clone, f"git clone {agent} failed", EXIT_ENV_ERROR)

    # --- 3. Write manifest + copy kit into the clone -------------------------
    _write_manifest(plan, clone_dest)
    kit_count = _copy_kit(plan, clone_dest, kit_src=kit_src, root=root)

    # --- 4. Stage everything -------------------------------------------------
    add = runner(["git", "-C", str(clone_dest), "add", "-A"])
    _check(add, "git add failed", EXIT_ENV_ERROR)

    # --- 5. The genesis commit ----------------------------------------------
    commit = runner(["git", "-C", str(clone_dest), "commit", "-m", _genesis_message(agent, desc)])
    _check(commit, "git commit (genesis) failed", EXIT_ENV_ERROR)

    # --- 6. Ensure the branch is named main ----------------------------------
    branch = runner(["git", "-C", str(clone_dest), "branch", "-M", "main"])
    _check(branch, "git branch -M main failed", EXIT_ENV_ERROR)

    # --- 7. Push the genesis commit to main ----------------------------------
    push = runner(["git", "-C", str(clone_dest), "push", "-u", "origin", "main"])
    _check(push, "git push origin main failed", EXIT_ENV_ERROR)

    return {
        "applied": True,
        "repo": agent,
        "clone_dest": str(clone_dest),
        "manifest_files": len(plan.manifest),
        "kit_files": kit_count,
        "pushed": True,
    }


# ---------------------------------------------------------------------------
# Internal write helpers (local filesystem only — not the runner seam)
# ---------------------------------------------------------------------------


def _check(result: RunResult, message: str, code: int) -> None:
    """Raise a typed GuildError if *result* is a failure."""
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise GuildError(
            code=code,
            message=f"{message}: {detail}" if detail else message,
            remediation="check `gh`/`git` output above and your repo permissions",
        )


def _write_manifest(plan: ProvisionPlan, dest_root: Path) -> None:
    """Write every manifest file into *dest_root*, creating parent dirs."""
    for relpath, content in plan.manifest.items():
        target = dest_root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _copy_kit(
    plan: ProvisionPlan,
    dest_root: Path,
    *,
    kit_src: dict[str, str] | None,
    root: Path | None,
) -> int:
    """Copy the canonical skill kit into *dest_root*; return the file count.

    The source map (``dest-relpath -> abs-source-path``) is either supplied via
    *kit_src* (tests) or reconstructed from :func:`copy_plan` (the values of
    that plan are the same dest relpaths the ProvisionPlan exposes in
    ``kit_dests``). We intersect with ``plan.kit_dests`` so the executor copies
    exactly what the plan promised.
    """
    if kit_src is None:
        if root is None:
            from guild.cli._repo import repo_root

            root = repo_root()
        # copy_plan: abs_src -> dest_relpath. Invert to dest_relpath -> abs_src.
        kit_src = {dest: src for src, dest in _copy_plan(Path(root)).items()}

    wanted = set(plan.kit_dests)
    count = 0
    for dest_rel, src in kit_src.items():
        if dest_rel not in wanted:
            continue
        target = dest_root / dest_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        count += 1
    return count
