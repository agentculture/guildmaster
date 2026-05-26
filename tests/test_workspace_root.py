"""Test workspace root resolution (guild/scaffold/workspace.resolve).

Tests the portable workspace-root resolution logic: ensures all three precedence
branches work correctly and no hardcoded home paths are ever embedded.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from guild.scaffold.workspace import resolve


class TestWorkspaceRootResolution:
    """Test the portable workspace-root resolution function."""

    def test_resolve_explicit_flag_takes_precedence(self):
        """Explicit --workspace-root flag is returned first."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            flag = Path(tmpdir) / "custom_workspace"
            flag.mkdir()
            local_cfg = {"workspace_root": "/some/other/path"}

            result = resolve(repo_root, flag, local_cfg)

            assert result == flag
            assert str(result) != "/some/other/path"

    def test_resolve_local_config_second_precedence(self):
        """Local config workspace_root is returned if flag is None."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            config_workspace = Path(tmpdir) / "configured_workspace"
            config_workspace.mkdir()
            local_cfg = {"workspace_root": str(config_workspace)}

            result = resolve(repo_root, None, local_cfg)

            assert result == config_workspace

    def test_resolve_parent_is_default(self):
        """repo_root.parent is returned when flag and config are absent."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()
            local_cfg = {}

            result = resolve(repo_root, None, local_cfg)

            assert result == workspace

    def test_resolve_parent_is_default_with_other_config_keys(self):
        """repo_root.parent is returned when workspace_root key is missing."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()
            local_cfg = {"some_other_key": "value"}

            result = resolve(repo_root, None, local_cfg)

            assert result == workspace

    def test_resolve_returns_pathlib_path(self):
        """Result is always a pathlib.Path, not a string."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            local_cfg = {}

            result = resolve(repo_root, None, local_cfg)

            assert isinstance(result, Path)

    def test_resolve_no_hardcoded_home_path_from_flag(self):
        """Explicit flag result never contains hardcoded /home/... path."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            flag = Path(tmpdir) / "workspace"
            flag.mkdir()

            result = resolve(repo_root, flag, {})

            assert not str(result).startswith("/home/")
            # Result is derived from the input flag (which we control)
            assert result == flag

    def test_resolve_no_hardcoded_home_path_from_config(self):
        """Config value with tilde is expanded, not hardcoded home."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            # Simulate a config with relative path (the normal case)
            local_cfg = {"workspace_root": str(repo_root.parent)}

            result = resolve(repo_root, None, local_cfg)

            assert not str(result).startswith("/home/")
            assert result == repo_root.parent

    def test_resolve_no_hardcoded_home_path_from_default(self):
        """Default (parent) result never contains hardcoded /home/... path."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()

            result = resolve(repo_root, None, {})

            # Result should never be a hardcoded home path
            assert not str(result).startswith("/home/")
            # Result should be derived from inputs (repo_root.parent)
            assert result == workspace

    def test_resolve_config_with_tilde_expansion(self):
        """Config value with tilde is expanded."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "guildmaster"
            repo_root.mkdir()
            # Config path with tilde should be expandable
            config_path = f"~/{Path(tmpdir).name}/workspace"
            local_cfg = {"workspace_root": config_path}

            result = resolve(repo_root, None, local_cfg)

            # Tilde expansion happens, result is a Path
            assert isinstance(result, Path)
            # Should not be the literal tilde string
            assert "~" not in str(result)

    def test_resolve_empty_local_cfg_dict(self):
        """Empty dict for local_cfg falls back to parent."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()

            result = resolve(repo_root, None, {})

            assert result == workspace

    def test_resolve_none_local_cfg_treated_as_empty(self):
        """None for local_cfg is treated like empty dict (falls back to parent)."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()

            result = resolve(repo_root, None, None)

            assert result == workspace

    def test_resolve_all_three_branches_with_relative_paths(self):
        """Exercise all three precedence branches with relative-style paths."""
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            repo_root = workspace / "guildmaster"
            repo_root.mkdir()
            config_root = workspace / "config_workspace"
            config_root.mkdir()
            flag_root = workspace / "flag_workspace"
            flag_root.mkdir()

            # Branch 1: explicit flag wins
            result1 = resolve(repo_root, flag_root, {"workspace_root": str(config_root)})
            assert result1 == flag_root

            # Branch 2: config when flag is None
            result2 = resolve(repo_root, None, {"workspace_root": str(config_root)})
            assert result2 == config_root

            # Branch 3: parent when flag and config are absent
            result3 = resolve(repo_root, None, {})
            assert result3 == workspace

            # All results are Paths, no hardcoded /home/...
            for res in [result1, result2, result3]:
                assert isinstance(res, Path)
                assert not str(res).startswith("/home/")
