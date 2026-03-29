"""Percival Internet Archive MCP server package."""

__all__ = ["main", "run"]
__version__ = "0.3.0"

from .server import main


def run() -> None:
    """Run module entrypoint lazily to avoid __main__ pre-import side effects."""
    from .__main__ import run as _run

    _run()
