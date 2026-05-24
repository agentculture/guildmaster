"""The package exposes a usable ``__version__`` string."""

from __future__ import annotations


def test_version_is_nonempty_string() -> None:
    from guild import __version__

    assert isinstance(__version__, str)
    assert __version__
