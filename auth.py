"""Compatibility shim for legacy `auth` imports."""

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

from percival_internetarchive_mcp.auth import init_auth as _init_auth
from percival_internetarchive_mcp.rollout import get_rollout_config


def init_auth():
    if not get_rollout_config().legacy_shims_enabled:
        raise RuntimeError(
            "Legacy auth shim is disabled by rollout policy."
        )
    return _init_auth()

__all__ = ["init_auth"]
