"""Compatibility shim for legacy `ia_bootstrap` imports."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_local_src_import_path() -> None:
    project_root = Path(__file__).resolve().parent
    src_root = (project_root / "src").resolve()
    package_root = src_root / "percival_internetarchive_mcp"
    if not package_root.is_dir():
        raise RuntimeError("Local MCP package path was not found under ./src.")

    src_root_str = str(src_root)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_local_src_import_path()

from percival_internetarchive_mcp.ia_bootstrap import ensure_internetarchive_import_path as _ensure_internetarchive_import_path
from percival_internetarchive_mcp.rollout import get_rollout_config


def ensure_internetarchive_import_path():
    if not get_rollout_config().legacy_shims_enabled:
        raise RuntimeError(
            "Legacy bootstrap shim is disabled by rollout policy."
        )
    return _ensure_internetarchive_import_path()

__all__ = ["ensure_internetarchive_import_path"]
