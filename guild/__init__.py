"""guild — an agent and CLI that manages skills for the AgentCulture mesh."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _v

try:
    __version__ = _v("guild-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
