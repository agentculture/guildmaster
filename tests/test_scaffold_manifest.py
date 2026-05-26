"""Tests for guild.scaffold.manifest — the pure file-map engine (t1).

TDD: these tests are written before the implementation.  They cover:

  criterion #1 — build() returns a relpath->content dict with all required files
  criterion #2 — writing the manifest to a tmp dir and running the generated
                 tests/test_cli_chassis.py passes with zero manual edits
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build():
    """Import the function under test (deferred so red tests show import errors)."""
    from guild.scaffold.manifest import build

    return build


REQUIRED_KEYS = [
    "pyproject.toml",
    "{pkg}/__init__.py",
    "{pkg}/__main__.py",
    "{pkg}/cli/__init__.py",
    "tests/test_cli_chassis.py",
    ".github/workflows/tests.yml",
    ".github/workflows/publish.yml",
    "CHANGELOG.md",
    "README.md",
    "LICENSE",
]


def _expand_keys(pkg: str) -> list[str]:
    return [k.format(pkg=pkg) for k in REQUIRED_KEYS]


# ---------------------------------------------------------------------------
# Criterion #1 — structural shape
# ---------------------------------------------------------------------------


class TestBuildReturnShape:
    """build() returns a non-empty dict with expected relpath keys."""

    def test_returns_dict(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert isinstance(result, dict)

    def test_all_required_keys_present(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        for key in _expand_keys("appsec"):
            assert key in result, f"Missing key: {key!r}"

    def test_package_name_derived_from_bare_name(self) -> None:
        """agentculture/appsec → package dir appsec/"""
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "appsec/__init__.py" in result
        assert "appsec/__main__.py" in result
        assert "appsec/cli/__init__.py" in result

    def test_no_owner_prefix_also_works(self) -> None:
        """plain 'appsec' (no owner) → package dir appsec/"""
        build = _build()
        result = build("appsec", "AppSec agent", "claude")
        assert "appsec/__init__.py" in result

    def test_all_values_are_nonempty_strings(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        for key, val in result.items():
            assert isinstance(val, str), f"{key}: value is not str"
            assert val.strip(), f"{key}: value is blank/whitespace"

    # --- pyproject.toml ---

    def test_pyproject_dist_name_is_pkg_cli(self) -> None:
        """dist name = '<name>-cli' (e.g. appsec-cli)."""
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert 'name = "appsec-cli"' in result["pyproject.toml"]

    def test_pyproject_has_hatchling_backend(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "hatchling" in result["pyproject.toml"]

    def test_pyproject_entry_point_matches_pkg(self) -> None:
        """scripts entry: appsec = 'appsec.cli:main'"""
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "appsec.cli:main" in result["pyproject.toml"]

    def test_pyproject_description_embedded(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "My Security Agent", "claude")
        assert "My Security Agent" in result["pyproject.toml"]

    # --- __init__.py ---

    def test_init_uses_importlib_metadata(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        init = result["appsec/__init__.py"]
        assert "importlib.metadata" in init
        assert "appsec-cli" in init  # version("appsec-cli")

    # --- LICENSE ---

    def test_license_is_mit(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        lic = result["LICENSE"]
        assert "MIT License" in lic
        assert "AgentCulture" in lic

    def test_license_has_year(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        import re

        assert re.search(r"20\d\d", result["LICENSE"]), "No year found in LICENSE"

    # --- CHANGELOG.md ---

    def test_changelog_starts_with_unreleased(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "Unreleased" in result["CHANGELOG.md"] or "0.1.0" in result["CHANGELOG.md"]

    # --- README.md ---

    def test_readme_mentions_agent_name(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "appsec" in result["README.md"].lower()

    # --- GitHub workflows ---

    def test_tests_yml_runs_pytest(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "pytest" in result[".github/workflows/tests.yml"]

    def test_publish_yml_has_pypi_job(self) -> None:
        build = _build()
        result = build("agentculture/appsec", "AppSec agent", "claude")
        assert "pypi" in result[".github/workflows/publish.yml"].lower()


# ---------------------------------------------------------------------------
# Criterion #2 — self-testing scaffold (write to disk + run generated test)
# ---------------------------------------------------------------------------


def _write_manifest(manifest: dict[str, str], root: Path) -> None:
    """Write all relpath->content entries to root."""
    for relpath, content in manifest.items():
        dest = root / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


class TestSelfTestingScaffold:
    """Write manifest to a tmp dir; the generated chassis test must pass."""

    def test_chassis_tests_pass_in_tmpdir(self, tmp_path: Path) -> None:
        """Criterion #2: zero manual edits needed after scaffold write."""
        build = _build()
        manifest = build("agentculture/appsec", "AppSec agent", "claude")
        _write_manifest(manifest, tmp_path)

        # Run the generated test file using the current Python interpreter.
        # Make the generated package importable by adding tmp_path to PYTHONPATH.
        import os

        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(tmp_path) + ((":" + python_path) if python_path else "")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(tmp_path / "tests" / "test_cli_chassis.py"),
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
            env=env,
        )
        assert result.returncode == 0, (
            f"Generated chassis test failed (exit {result.returncode}).\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}\n"
        )

    def test_chassis_tests_pass_for_second_agent(self, tmp_path: Path) -> None:
        """Reproducibility: a different agent name also self-tests green."""
        build = _build()
        manifest = build("agentculture/guardian", "Guardian agent", "acp")
        _write_manifest(manifest, tmp_path)

        import os

        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(tmp_path) + ((":" + python_path) if python_path else "")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(tmp_path / "tests" / "test_cli_chassis.py"),
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
            env=env,
        )
        assert result.returncode == 0, (
            f"Chassis test for 'guardian' failed (exit {result.returncode}).\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}\n"
        )
