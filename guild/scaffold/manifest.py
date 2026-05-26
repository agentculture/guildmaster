"""Pure file-map engine for the afi-cli scaffold.

``build(agent, desc, backend)`` returns a ``dict[str, str]`` mapping
relative paths to file contents — the complete skeleton for a brand-new
AgentCulture sibling Python package that follows the afi-cli pattern
(same layout as guildmaster itself).

This module is intentionally **pure**: no file I/O, no subprocess calls,
no network access.  Callers write the returned dict to disk themselves.
"""

from __future__ import annotations

import datetime

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["build"]


def build(agent: str, desc: str, backend: str) -> dict[str, str]:
    """Return the full relpath → content file map for a new sibling agent.

    Parameters
    ----------
    agent:
        The agent identifier, either ``owner/repo`` (e.g.
        ``agentculture/appsec``) or a bare name (e.g. ``appsec``).
        The package name is derived from the repo / bare name portion.
    desc:
        Short one-line description of the agent.
    backend:
        Culture backend (e.g. ``claude``, ``acp``).

    Returns
    -------
    dict[str, str]
        A mapping from relative file path to its text content.  All
        paths use forward slashes and are relative to the new repo root.
    """
    pkg = _pkg_from_agent(agent)
    dist = f"{pkg}-cli"
    binary = pkg
    year = str(datetime.date.today().year)

    files: dict[str, str] = {}

    files["pyproject.toml"] = _pyproject(pkg, dist, binary, desc)
    files[f"{pkg}/__init__.py"] = _pkg_init(pkg, dist, desc)
    files[f"{pkg}/__main__.py"] = _pkg_main(pkg)
    files[f"{pkg}/cli/__init__.py"] = _cli_init(pkg, binary, dist)
    files[f"{pkg}/cli/_errors.py"] = _cli_errors(pkg)
    files[f"{pkg}/cli/_output.py"] = _cli_output(pkg)
    files["tests/test_cli_chassis.py"] = _test_chassis(pkg, binary, dist)
    files[".github/workflows/tests.yml"] = _tests_workflow(pkg, binary)
    files[".github/workflows/publish.yml"] = _publish_workflow(pkg, dist)
    files["CHANGELOG.md"] = _changelog(pkg)
    files["README.md"] = _readme(pkg, binary, desc)
    files["LICENSE"] = _license(year)

    return files


# ---------------------------------------------------------------------------
# Package-name derivation
# ---------------------------------------------------------------------------


def _pkg_from_agent(agent: str) -> str:
    """Derive the Python package name from the agent string.

    ``agentculture/appsec`` → ``appsec``
    ``appsec``              → ``appsec``
    """
    return agent.split("/")[-1].lower().replace("-", "_")


# ---------------------------------------------------------------------------
# Template renderers — each returns a str
# ---------------------------------------------------------------------------

_PYPROJECT_TMPL = """\
[project]
name = "{dist}"
version = "0.1.0"
description = "{desc}"
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [{{name = "AgentCulture"}}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: MIT License",
    "Topic :: Software Development",
    "Intended Audience :: Developers",
]
dependencies = [
    "pyyaml>=6.0",
]

[project.urls]
Homepage = "https://github.com/agentculture/{pkg}"
Issues = "https://github.com/agentculture/{pkg}/issues"

[project.scripts]
{binary} = "{pkg}.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["{pkg}"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-xdist>=3.0",
    "pytest-cov>=4.1",
    "bandit>=1.7.5",
    "flake8>=6.1",
    "isort>=5.12.0",
    "black>=23.7.0",
]

[tool.coverage.run]
source = ["{pkg}"]
omit = ["{pkg}/__pycache__/*"]

[tool.coverage.report]
fail_under = 60
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "if TYPE_CHECKING:",
]

[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["{pkg}"]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.bandit]
exclude_dirs = ["tests"]
skips = ["B101", "B404", "B603"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
"""


def _pyproject(pkg: str, dist: str, binary: str, desc: str) -> str:
    return _PYPROJECT_TMPL.format(pkg=pkg, dist=dist, binary=binary, desc=desc)


# ---------------------------------------------------------------------------

_PKG_INIT_TMPL = '"""{pkg} — {desc}."""\n\nfrom importlib.metadata import PackageNotFoundError\nfrom importlib.metadata import version as _v\n\ntry:\n    __version__ = _v("{dist}")\nexcept PackageNotFoundError:\n    __version__ = "0.0.0+local"\n\n__all__ = ["__version__"]\n'  # noqa: E501


def _pkg_init(pkg: str, dist: str, desc: str) -> str:
    return _PKG_INIT_TMPL.format(pkg=pkg, dist=dist, desc=desc)


# ---------------------------------------------------------------------------

_PKG_MAIN_TMPL = '"""Allow running {pkg} as ``python -m {pkg}``."""\n\nimport sys\n\nfrom {pkg}.cli import main\n\nif __name__ == "__main__":\n    sys.exit(main())\n'  # noqa: E501


def _pkg_main(pkg: str) -> str:
    return _PKG_MAIN_TMPL.format(pkg=pkg)


# ---------------------------------------------------------------------------

_CLI_INIT_TMPL = '''\
"""Unified CLI entry point for {pkg}.

Every handler raises :class:`{pkg}.cli._errors.{Pkg}Error` on failure;
``main()`` catches it via ``_dispatch`` and routes through
:mod:`{pkg}.cli._output`.
"""

from __future__ import annotations

import argparse
import sys

from {pkg} import __version__
from {pkg}.cli._errors import EXIT_USER_ERROR, {Pkg}Error
from {pkg}.cli._output import emit_error


class _{Pkg}ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`."""

    def error(self, message: str) -> None:  # type: ignore[override]
        err = {Pkg}Error(
            code=EXIT_USER_ERROR,
            message=message,
            remediation=f"run \'{{self.prog}} --help\' to see valid arguments",
        )
        emit_error(err)
        raise SystemExit(err.code)


def _build_parser() -> argparse.ArgumentParser:
    parser = _{Pkg}ArgumentParser(
        prog="{binary}",
        description="{binary} — {desc}",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {{__version__}}",
    )
    parser.add_subparsers(dest="command", parser_class=_{Pkg}ArgumentParser)
    return parser


def _dispatch(args: argparse.Namespace) -> int:
    if not hasattr(args, "func") or args.func is None:
        return 0
    try:
        rc = args.func(args)
    except {Pkg}Error as err:
        emit_error(err)
        return err.code
    except Exception as err:  # noqa: BLE001
        wrapped = {Pkg}Error(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {{err.__class__.__name__}}: {{err}}",
            remediation="file a bug at https://github.com/agentculture/{pkg}/issues",
        )
        emit_error(wrapped)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
'''


def _cli_init(pkg: str, binary: str, dist: str) -> str:  # noqa: ARG001
    Pkg = pkg.capitalize()
    # Handle underscored names: appsec → Appsec, my_agent → My_agent → use title
    Pkg = "".join(w.capitalize() for w in pkg.split("_"))
    desc_placeholder = f"{binary} agent"
    return _CLI_INIT_TMPL.format(pkg=pkg, Pkg=Pkg, binary=binary, desc=desc_placeholder)


# ---------------------------------------------------------------------------

_CLI_ERRORS_TMPL = '''\
"""Typed error and exit-code policy for {pkg}."""

from __future__ import annotations

from dataclasses import dataclass

EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1
EXIT_ENV_ERROR = 2


@dataclass
class {Pkg}Error(Exception):
    """Structured error raised within {pkg}; carries a remediation hint."""

    code: int
    message: str
    remediation: str = ""

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {{
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }}
'''


def _cli_errors(pkg: str) -> str:
    Pkg = "".join(w.capitalize() for w in pkg.split("_"))
    return _CLI_ERRORS_TMPL.format(pkg=pkg, Pkg=Pkg)


# ---------------------------------------------------------------------------

_CLI_OUTPUT_TMPL = '''\
"""stdout / stderr helpers for {pkg}."""

from __future__ import annotations

import sys
from typing import Any, TextIO

from {pkg}.cli._errors import {Pkg}Error


def emit_result(data: Any, *, stream: TextIO | None = None) -> None:
    """Write a command result to stdout."""
    s = stream if stream is not None else sys.stdout
    text = data if isinstance(data, str) else str(data)
    s.write(text)
    if not text.endswith("\\n"):
        s.write("\\n")


def emit_error(err: {Pkg}Error, *, stream: TextIO | None = None) -> None:
    """Write a :class:`{Pkg}Error` to stderr."""
    s = stream if stream is not None else sys.stderr
    s.write(f"error: {{err.message}}\\n")
    if err.remediation:
        s.write(f"hint: {{err.remediation}}\\n")
'''


def _cli_output(pkg: str) -> str:
    Pkg = "".join(w.capitalize() for w in pkg.split("_"))
    return _CLI_OUTPUT_TMPL.format(pkg=pkg, Pkg=Pkg)


# ---------------------------------------------------------------------------

_CHASSIS_TEST_TMPL = '''\
"""Chassis tests for the {pkg} CLI skeleton.

These tests exercise the generated CLI surface (--version / --help /
python -m {pkg}) and verify the pyproject.toml entry-point declaration.
They are generated by guild scaffold and must pass with zero manual edits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# Resolve the repo root relative to this test file so tests work when
# invoked from any cwd (the scaffold writes tests/ at repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_flag_prints_version_and_exits_zero() -> None:
    """`{binary} --version` exits 0 and prints a non-empty version string."""
    from {pkg}.cli import main

    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0


def test_no_args_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """`{binary}` with no args prints usage and returns 0."""
    from {pkg}.cli import main

    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage: {binary}" in out


def test_python_m_pkg_version() -> None:
    """`python -m {pkg} --version` works (proves __main__.py)."""
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + (
        (":" + env["PYTHONPATH"]) if env.get("PYTHONPATH") else ""
    )
    result = subprocess.run(
        [sys.executable, "-m", "{pkg}", "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode == 0


def test_pyproject_entry_point_declared() -> None:
    """pyproject.toml declares the {binary} script entry point."""
    import tomllib

    data = tomllib.load(open(REPO_ROOT / "pyproject.toml", "rb"))
    scripts = data.get("project", {{}}).get("scripts", {{}})
    assert "{binary}" in scripts, "Missing '{binary}' entry in [project.scripts]"
    assert "{pkg}.cli:main" in scripts["{binary}"]
'''


def _test_chassis(pkg: str, binary: str, dist: str) -> str:  # noqa: ARG001
    return _CHASSIS_TEST_TMPL.format(pkg=pkg, binary=binary, dist=dist)


# ---------------------------------------------------------------------------

_TESTS_YML_TMPL = """\
name: Tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v4

      - run: uv python install 3.12

      - run: uv sync

      - run: uv run pytest -n auto --cov={pkg} --cov-report=xml:coverage.xml --cov-report=term -v

  lint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - run: uv python install 3.12

      - run: uv sync

      - name: black --check
        run: uv run black --check {pkg} tests

      - name: isort --check
        run: uv run isort --check-only {pkg} tests

      - name: flake8
        run: uv run flake8 {pkg} tests

      - name: bandit
        run: uv run bandit -c pyproject.toml -r {pkg}

  version-check:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - run: git fetch origin main

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Check version bump
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: |
          _PY='import tomllib, sys'
          _LOAD='tomllib.load(open("pyproject.toml","rb"))["project"]["version"]'
          _LOADS='tomllib.loads(sys.stdin.read())["project"]["version"]'
          PR_VERSION=$(python3 -c "$_PY; print($_LOAD)")
          MAIN_VERSION=$(
            git show origin/main:pyproject.toml 2>/dev/null |
            python3 -c "$_PY; print($_LOADS)" 2>/dev/null || echo ""
          )
          if [ -z "$MAIN_VERSION" ]; then
            echo "No pyproject.toml on main yet — skipping version check."
            exit 0
          fi
          if [ "$PR_VERSION" = "$MAIN_VERSION" ]; then
            echo "::error::Version $PR_VERSION matches main. Bump before merging."
            exit 1
          else
            echo "Version bumped: $MAIN_VERSION -> $PR_VERSION"
          fi
"""


def _tests_workflow(pkg: str, binary: str) -> str:  # noqa: ARG001
    return _TESTS_YML_TMPL.format(pkg=pkg, binary=binary)


# ---------------------------------------------------------------------------

_PUBLISH_YML_TMPL = """\
name: Publish to PyPI

on:
  push:
    branches: [main]
    paths:
      - "pyproject.toml"
      - "{pkg}/**"
  pull_request:
    branches: [main]
    paths:
      - "pyproject.toml"
      - "{pkg}/**"

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - run: uv python install 3.12

      - run: uv sync

      - run: uv run pytest -n auto -v

  test-publish:
    if: >-
      github.event_name == 'pull_request' &&
      github.event.pull_request.head.repo.full_name == github.repository
    needs: test
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - run: uv python install 3.12

      - run: uv sync

      - name: Set dev version
        run: |
          _PY='import tomllib'
          _PY="$_PY; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
          BASE=$(uv run python -c "$_PY")
          DEV_VERSION="${{BASE}}.dev${{{{ github.run_number }}}}"
          sed -i "s/^version = .*/version = \\"${{DEV_VERSION}}\\"/" pyproject.toml
          echo "DEV_VERSION=${{DEV_VERSION}}" >> "$GITHUB_ENV"

      - name: Build and publish to TestPyPI
        run: |
          uv build
          uv publish \
            --publish-url https://test.pypi.org/legacy/ \
            --trusted-publishing always \
            --check-url https://test.pypi.org/simple/

  publish:
    if: github.event_name == 'push'
    needs: test
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4

      - run: uv python install 3.12

      - run: uv sync

      - name: Build and publish to PyPI
        run: |
          uv build
          uv publish --trusted-publishing always --check-url https://pypi.org/simple/
"""


def _publish_workflow(pkg: str, dist: str) -> str:  # noqa: ARG001
    return _PUBLISH_YML_TMPL.format(pkg=pkg, dist=dist)


# ---------------------------------------------------------------------------

_CHANGELOG_TMPL = """\
# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - {year}

### Added

- Initial scaffold generated by `guild create`.
"""


def _changelog(pkg: str) -> str:  # noqa: ARG001
    year = str(datetime.date.today().year)
    return _CHANGELOG_TMPL.format(year=year)


# ---------------------------------------------------------------------------

_README_TMPL = """\
# {pkg}

{desc}

{pkg} is a sibling in the [AgentCulture](https://github.com/agentculture) mesh.
The repo and the Culture agent are named `{pkg}`; the CLI ships as `{dist}` on
PyPI and installs the `{binary}` binary.

## Install

```bash
# From PyPI (Trusted Publishing):
uv tool install {dist}

# From source (dev):
uv sync
uv run {binary} --version
```

## Commands

```bash
uv run {binary} --help
```

## Develop

```bash
uv sync
uv run pytest -n auto -v
uv run black --check {pkg} tests && uv run isort --check-only {pkg} tests
uv run flake8 {pkg} tests && uv run bandit -c pyproject.toml -r {pkg}
```

Every PR bumps the version (CI's `version-check` enforces it):

```bash
python3 .claude/skills/version-bump/scripts/bump.py patch
```
"""


def _readme(pkg: str, binary: str, desc: str) -> str:
    dist = f"{pkg}-cli"
    return _README_TMPL.format(pkg=pkg, binary=binary, desc=desc, dist=dist)


# ---------------------------------------------------------------------------

_LICENSE_TMPL = """\
MIT License

Copyright (c) {year} AgentCulture

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _license(year: str) -> str:
    return _LICENSE_TMPL.format(year=year)
