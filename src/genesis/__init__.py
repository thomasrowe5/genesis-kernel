"""Genesis Kernel application package."""

from importlib.metadata import version

__all__ = ["__version__"]

try:
    __version__ = version("genesis-kernel")
except Exception:  # pragma: no cover
    __version__ = "0.0.0"
