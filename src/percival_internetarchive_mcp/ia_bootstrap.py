from __future__ import annotations

import sys
from pathlib import Path


def ensure_internetarchive_import_path() -> None:
    """Ensure imports resolve to the vendored `internetarchive` package source."""
    # package file -> .../percival-internetarchive-mcp/src/percival_internetarchive_mcp/ia_bootstrap.py
    # we want .../percival-internetarchive-mcp/internetarchive
    project_root = Path(__file__).resolve().parents[2]
    vendored_src_root = project_root / "internetarchive"
    if not vendored_src_root.is_dir():
        return
    vendored_package_marker = vendored_src_root / "internetarchive" / "__init__.py"
    if not vendored_package_marker.is_file():
        return

    path_str = str(vendored_src_root)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
