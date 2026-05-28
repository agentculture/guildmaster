"""Pure transform for the template-instantiate approach to ``guild create``.

Given a freshly-cloned copy of ``agentculture/culture-agent-template`` at *dest*,
this module customises it in-place into a new sibling agent identified by *bare*
(the repo/suffix token, e.g. ``appsec`` or ``my-agent``).

Public API
----------
rename_map(bare) -> dict[str, str]
    The two identifier substitutions: ``culture_agent_template`` → ``pkg`` and
    ``culture-agent-template`` → ``repo_token``.  Pure function; no I/O.

transform_plan(bare, desc) -> dict
    A human/JSON-renderable description of what ``transform_clone`` WOULD do
    (the rename map, package directory rename, pyproject description, README
    headline change, and CLAUDE.md seed replacement).  No I/O.

transform_clone(dest, bare, desc, backend) -> None
    The actual, irreversible in-place transform.  Walks *dest*, skipping
    ``.git/``:
    1. Global text replace across every file: ``culture_agent_template`` → pkg,
       then ``culture-agent-template`` → repo_token.  (Underscore form first so
       it is not partially clobbered — though they don't overlap, underscore
       first is the safe order.)
    2. Rename the package directory ``culture_agent_template/`` → ``pkg/``.
    3. In ``pyproject.toml`` set ``description = "<desc>"``.
    4. In ``README.md`` replace the first heading text with the new agent name
       and embed *desc* as the sub-heading or first paragraph.
    5. Overwrite ``CLAUDE.md`` with a self-init seed (prompt-file-present +
       backend-consistency compliant; carries an explicit ``/init`` re-init
       instruction; names the agent, embeds *desc*, uses *backend*).

This module is PURE w.r.t. the filesystem: it only writes within *dest*, and
only after the caller hands it a real directory.  No subprocess, no network.
Unit tests pass a ``tmp_path`` fixture dir populated with a minimal fixture tree.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Identifier derivation
# ---------------------------------------------------------------------------

_TEMPLATE_PKG = "culture_agent_template"  # underscore form
_TEMPLATE_REPO = "culture-agent-template"  # hyphen form

_BACKEND_PROMPT_FILE: dict[str, str] = {
    "claude": "CLAUDE.md",
    "acp": "AGENTS.md",
}


def _derive(bare: str) -> tuple[str, str]:
    """Return ``(pkg, repo_token)`` from the bare repo name.

    ``repo_token`` is the hyphen form; ``pkg`` is the underscore / lower-case form.

    Examples
    --------
    >>> _derive("appsec")
    ('appsec', 'appsec')
    >>> _derive("my-agent")
    ('my_agent', 'my-agent')
    """
    repo_token = bare.lower()
    pkg = repo_token.replace("-", "_")
    return pkg, repo_token


# ---------------------------------------------------------------------------
# Public helpers — no I/O
# ---------------------------------------------------------------------------


def rename_map(bare: str) -> dict[str, str]:
    """Return the two identifier substitutions for the transform.

    The dict is ordered:  **underscore form first** (so neither replace
    accidentally clobbers the other).

    Parameters
    ----------
    bare:
        The bare repo/agent name (e.g. ``"appsec"``, ``"my-agent"``).

    Returns
    -------
    dict[str, str]
        ``{old_token: new_token}`` — two entries, underscore form then hyphen.
    """
    pkg, repo_token = _derive(bare)
    return {_TEMPLATE_PKG: pkg, _TEMPLATE_REPO: repo_token}


def transform_plan(bare: str, desc: str, dist: str | None = None) -> dict:
    """Return a human/JSON-renderable description of what ``transform_clone`` would do.

    Parameters
    ----------
    bare:
        The bare repo/agent name.
    desc:
        The short description for the new agent.
    dist:
        The PyPI distribution name to set. ``None`` (the default) means leave it
        as the global-replace result (``repo_token``) — the pure default. When it
        differs from ``repo_token``, an extra retarget step renames just the dist
        (``[project].name``, the ``importlib.metadata`` lookup, and the TestPyPI
        install pin); the importable package and the console command stay
        ``repo_token``.

    Returns
    -------
    dict with keys:
        ``rename_map``           — ``{old: new}`` substitution pairs
        ``package_dir_rename``   — ``{old_dir: new_dir}``
        ``pyproject_desc``       — the value that would be written to ``description``
        ``dist``                 — the effective distribution name
        ``claude_md_seed``       — the first ~3 lines of the seed (synopsis only)
        ``steps``                — ordered list of step descriptions
    """
    pkg, repo_token = _derive(bare)
    effective_dist = dist if dist else repo_token
    m = rename_map(bare)
    steps = [
        f"global text replace in every file (skip .git/): "
        f"{_TEMPLATE_PKG!r} → {pkg!r}, then {_TEMPLATE_REPO!r} → {repo_token!r}",
        f"rename package directory {_TEMPLATE_PKG!r} → {pkg!r}",
        f"set description in pyproject.toml to {desc!r}",
        "replace README.md first heading + intro with new agent name and description",
        "overwrite CLAUDE.md with a self-init seed (names agent, embeds desc, /init instruction)",
    ]
    if effective_dist != repo_token:
        steps.append(
            f"retarget PyPI distribution name {repo_token!r} → {effective_dist!r} "
            "([project].name, importlib.metadata lookup, TestPyPI install pin); "
            f"command + import package stay {repo_token!r}"
        )
    return {
        "bare": bare,
        "pkg": pkg,
        "repo_token": repo_token,
        "rename_map": m,
        "package_dir_rename": {_TEMPLATE_PKG: pkg},
        "pyproject_desc": desc,
        "dist": effective_dist,
        "claude_md_seed_synopsis": f"# CLAUDE.md seed for {bare} — run /init to expand",
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# CLAUDE.md seed generator
# ---------------------------------------------------------------------------


def _seed_prompt(bare: str, desc: str, backend: str) -> str:
    """Render the CLAUDE.md (or AGENTS.md) seed for a new sibling.

    This is intentionally minimal — a *seed* the new agent will expand via
    ``/init``.  It must:
      - identify itself as a seed/placeholder,
      - name the agent and embed the description,
      - carry an explicit, actionable re-init instruction,
      - remain valid for ``steward doctor`` (prompt-file-present; backend-consistency).
    """
    prompt_file = _BACKEND_PROMPT_FILE[backend]
    return f"""\
# {prompt_file} — seed / bootstrap placeholder

> **This is a self-initializing seed, not a finished runtime prompt.**
> Run `/init` (or describe the agent's domain to your AI assistant) to
> re-initialize this file into a full runtime prompt, using the description
> below and the scaffolded repo as context.

## Agent

This repository hosts the **{bare}** agent.

## Description

{desc.rstrip()}

## Re-init instruction

This file is a seed. To expand it into your full runtime prompt:

1. Open this repo in Claude Code (or your preferred AI assistant).
2. Run `/init` — the assistant will read the repo, incorporate the description
   above, and replace this seed with a complete `{prompt_file}`.
3. Commit the result.

Until you run `/init`, `{bare}` satisfies the `steward doctor`
`prompt-file-present` and `backend-consistency` invariants (a `{prompt_file}`
exists and `culture.yaml` declares `backend: {backend}`) but the prompt is not
yet tailored to this agent's domain.
"""


# ---------------------------------------------------------------------------
# The transform itself
# ---------------------------------------------------------------------------


def _all_files(dest: Path) -> list[Path]:
    """Return all regular files under *dest*, skipping ``.git/``."""
    results: list[Path] = []
    for p in sorted(dest.rglob("*")):
        # Skip anything inside .git/
        if ".git" in p.relative_to(dest).parts:
            continue
        if p.is_file() and not p.is_symlink():
            results.append(p)
    return results


def _text_replace_file(path: Path, replacements: dict[str, str]) -> None:
    """Apply *replacements* (in order) to the text content of *path*.

    Silently skips files that cannot be decoded as UTF-8 (binary assets).
    """
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    text = original
    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        path.write_text(text, encoding="utf-8")


def _toml_escape(s: str) -> str:
    """Escape *s* for a TOML basic (double-quoted) string.

    Backslash first (so the escapes added below aren't doubled), then quote and
    control chars — a ``--desc`` containing ``\\``, ``"`` or a newline would
    otherwise produce invalid TOML.
    """
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _set_pyproject_description(pyproject: Path, desc: str) -> None:
    """Replace the ``description = "..."`` line in *pyproject* with *desc*.

    Handles both single and double quotes.  If the line is not found the file
    is left unchanged (graceful degradation for unusual pyproject layouts).
    """
    if not pyproject.is_file():
        return
    try:
        text = pyproject.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return
    # Match: description = "..." or description = '...'
    new_text = re.sub(
        r'^(description\s*=\s*)["\'][^"\']*["\']',
        lambda m: m.group(1) + '"' + _toml_escape(desc) + '"',
        text,
        flags=re.MULTILINE,
    )
    if new_text != text:
        pyproject.write_text(new_text, encoding="utf-8")


def _retarget_dist(dest: Path, pkg: str, repo_token: str, dist: str) -> None:
    """Rename only the PyPI **distribution** from *repo_token* to *dist*.

    Called after the global token replace has set every ``culture-agent-template``
    occurrence to *repo_token*. This narrowly rewrites the three places that name
    the *distribution* (as opposed to the importable package or the console
    command, which stay *repo_token*):

    1. ``pyproject.toml`` — the ``[project].name = "<repo_token>"`` line.
    2. ``<pkg>/__init__.py`` — the ``importlib.metadata`` version lookup argument
       (the ``"<repo_token>"`` string literal).
    3. ``.github/workflows/publish.yml`` — the TestPyPI install hint's version
       pin (``<repo_token>==`` → ``<dist>==``).

    Each step degrades gracefully if the file or the expected pattern is absent,
    so a template that lays these out differently is left as-is rather than
    corrupted. No-op is the caller's responsibility (skip when ``dist`` equals
    ``repo_token``).
    """
    # 1. pyproject [project].name — match only the line whose value is repo_token,
    #    so authors `{name = "..."}` and other `name =` lines are never touched.
    pyproject = dest / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = None
        if text is not None:
            new_text = re.sub(
                r'(?m)^(\s*name\s*=\s*)["\']' + re.escape(repo_token) + r'["\']',
                lambda m: m.group(1) + '"' + dist + '"',
                text,
            )
            if new_text != text:
                pyproject.write_text(new_text, encoding="utf-8")

    # 2. <pkg>/__init__.py — the metadata lookup argument string literal.
    init_py = dest / pkg / "__init__.py"
    if init_py.is_file():
        try:
            text = init_py.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = None
        if text is not None:
            new_text = text.replace(f'"{repo_token}"', f'"{dist}"').replace(
                f"'{repo_token}'", f"'{dist}'"
            )
            if new_text != text:
                init_py.write_text(new_text, encoding="utf-8")

    # 3. publish.yml — the TestPyPI install pin (`<repo_token>==`). The `==`
    #    anchors it to a version pin so other repo_token mentions are untouched.
    publish = dest / ".github" / "workflows" / "publish.yml"
    if publish.is_file():
        try:
            text = publish.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = None
        if text is not None:
            new_text = text.replace(f"{repo_token}==", f"{dist}==")
            if new_text != text:
                publish.write_text(new_text, encoding="utf-8")


def _is_desc_stub(line: str) -> bool:
    """Return True if *line* looks like a short plain-text description placeholder.

    A stub is a non-empty line that has no markdown structural prefix (heading,
    blockquote, badge/link, code fence, list item) and is under 200 characters.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) >= 200:
        return False
    return not re.match(r"^[#>`\-\*!\[]", stripped)


def _is_block_start(line: str) -> bool:
    """Return True if *line* begins a new markdown block.

    Used to bound intro-paragraph consumption in ``_replace_heading_block`` so a
    block that immediately follows the intro *without* a blank line (e.g. ``##
    Section``, a list, or a badge row) is not swallowed.  Recognised starts:
    ATX headings (``#``), blockquotes (``>``), unordered list items
    (``- ``/``* ``/``+ ``), links/badges (``[`` / ``![``), and fenced code
    (```` ``` ```` / ``~~~``).

    A *single* leading backtick is **not** a block start — it is inline code in
    wrapped prose (e.g. ``` `culture.yaml`, and you have… ```), which is part of
    the intro paragraph and must be consumed with it.
    """
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith(("```", "~~~")):
        return True
    if stripped[0] in "#>":
        return True
    if stripped.startswith(("![", "[")):
        return True
    if stripped[:2] in ("- ", "* ", "+ "):
        return True
    return False


def _replace_heading_block(lines: list[str], i: int, bare: str, desc: str) -> tuple[list[str], int]:
    """Replace the heading at *lines[i]* and its following description stub.

    Returns ``(out_lines, new_i)`` — the output lines for the heading block and
    the index of the next unconsumed line.
    """
    out: list[str] = [f"# {bare}\n"]
    i += 1

    # Pass through blank lines that follow the heading.
    while i < len(lines) and lines[i].strip() == "":
        out.append(lines[i])
        i += 1

    # Replace or insert the description.
    if i < len(lines) and _is_desc_stub(lines[i]):
        out.append(desc + "\n")
        i += 1
        # Consume the rest of the intro paragraph so a *multi-line* template
        # intro is replaced wholesale rather than leaving a dangling fragment.
        # Stop at a blank line (paragraph end) OR the start of a new markdown
        # block (heading/list/blockquote/badge/fence) — even when no blank line
        # separates it — so a following block is never silently dropped.  A
        # single leading backtick stays consumable (wrapped inline-code prose).
        while i < len(lines) and lines[i].strip() != "" and not _is_block_start(lines[i]):
            i += 1
    elif i < len(lines):
        out.append(desc + "\n\n")
    else:
        out.append(desc + "\n")

    return out, i


def _set_readme_intro(readme: Path, bare: str, desc: str) -> None:
    """Replace the first ``#`` heading in *readme* with the new agent name and
    insert *desc* as the first paragraph if not already present.

    Strategy: replace the first ``# <anything>`` line with ``# {bare}``; if the
    very next non-blank line looks like a description stub (no markdown
    structure, short), replace it with *desc*.  Otherwise insert *desc* as a
    new paragraph after the heading.

    This keeps the README navigable without destroying any custom body text the
    template may have below the intro block.
    """
    if not readme.is_file():
        return
    try:
        text = readme.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    replaced_heading = False

    while i < len(lines):
        line = lines[i]
        if not replaced_heading and re.match(r"^#\s", line):
            heading_out, i = _replace_heading_block(lines, i, bare, desc)
            out.extend(heading_out)
            replaced_heading = True
            continue
        out.append(line)
        i += 1

    if not replaced_heading:
        # No heading found — prepend.
        out = [f"# {bare}\n\n{desc}\n\n"] + out

    readme.write_text("".join(out), encoding="utf-8")


def transform_clone(
    dest: Path,
    bare: str,
    desc: str,
    backend: str = "claude",
    dist: str | None = None,
) -> None:
    """Customise the cloned template tree at *dest* into the new agent *bare*.

    This function performs the complete in-place transform:

    1. **Global text replace** across every file (skipping ``.git/``):
       ``culture_agent_template`` → pkg, then ``culture-agent-template`` →
       repo_token.  (Underscore form first — safe order.)
    2. **Rename** the package directory ``culture_agent_template/`` → ``pkg/``.
    3. **Set description** in ``pyproject.toml``.
    4. **Rewrite README.md** first heading + intro.
    5. **Overwrite CLAUDE.md** (or ``AGENTS.md`` for acp) with a self-init seed.
    6. **Retarget the PyPI dist name** to *dist* (only when it differs from
       ``repo_token``) — ``[project].name``, the ``importlib.metadata`` lookup,
       and the TestPyPI install pin. The importable package and the console
       command stay ``repo_token``.

    Parameters
    ----------
    dest:
        The root of the cloned template working tree.
    bare:
        Bare repo/agent name (e.g. ``"appsec"``, ``"my-agent"``).
    desc:
        Short description for the new agent.
    backend:
        ``"claude"`` (default) or ``"acp"``.
    dist:
        PyPI distribution name. ``None`` leaves it as ``repo_token`` (the pure
        default); a different value retargets only the dist (step 6).

    Raises
    ------
    ValueError
        If *backend* is not recognised.
    FileNotFoundError
        If *dest* does not exist or is not a directory.
    """
    if backend not in _BACKEND_PROMPT_FILE:
        raise ValueError(
            f"backend must be one of {sorted(_BACKEND_PROMPT_FILE)!r}, got {backend!r}"
        )
    if not dest.is_dir():
        raise FileNotFoundError(f"dest is not a directory: {dest}")

    pkg, repo_token = _derive(bare)
    replacements = rename_map(bare)  # underscore first, then hyphen

    # Step 1 — global text replace (visit all files before the directory rename
    # so the package dir's own files are updated while still reachable).
    for path in _all_files(dest):
        _text_replace_file(path, replacements)

    # Step 2 — rename the package directory.
    old_pkg_dir = dest / _TEMPLATE_PKG
    new_pkg_dir = dest / pkg
    if old_pkg_dir.is_dir() and old_pkg_dir != new_pkg_dir:
        old_pkg_dir.rename(new_pkg_dir)

    # Step 3 — set description in pyproject.toml.
    _set_pyproject_description(dest / "pyproject.toml", desc)

    # Step 4 — rewrite README.md first heading + intro.
    _set_readme_intro(dest / "README.md", bare, desc)

    # Step 5 — overwrite CLAUDE.md (or AGENTS.md) with a self-init seed.
    prompt_file = _BACKEND_PROMPT_FILE[backend]
    seed_content = _seed_prompt(bare, desc, backend)
    (dest / prompt_file).write_text(seed_content, encoding="utf-8")

    # Step 6 — retarget the PyPI dist name (only when it differs from repo_token,
    # so the default is a true no-op and the bare-name case is unchanged).
    if dist and dist != repo_token:
        _retarget_dist(dest, pkg, repo_token, dist)
