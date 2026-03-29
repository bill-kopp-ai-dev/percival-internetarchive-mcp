"""Module entrypoint for `python -m percival_internetarchive_mcp`."""

from __future__ import annotations

import logging
import sys

from .server import main


def run() -> None:
    """Run MCP server with stdio transport."""
    try:
        main()
    except KeyboardInterrupt:
        print("\nInternet Archive MCP server stopped by user.", file=sys.stderr)
    except Exception as exc:
        logging.getLogger(__name__).critical(
            "Server exited with a critical error: %s", exc, exc_info=True
        )
        sys.exit(1)


if __name__ == "__main__":
    run()
