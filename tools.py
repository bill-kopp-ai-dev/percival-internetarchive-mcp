"""Compatibility shim for legacy `tools` imports."""

from __future__ import annotations

import logging
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

from percival_internetarchive_mcp.archive_tools import (
    download_archive_file,
    get_archive_metadata,
    search_archive,
    set_archive_session,
)
from percival_internetarchive_mcp.contracts import error_response
from percival_internetarchive_mcp.rollout import get_rollout_config


logger = logging.getLogger(__name__)


def _legacy_disabled_response(tool_name: str):
    return error_response(
        tool_name,
        "LEGACY_API_DISABLED",
        "Legacy compatibility shim is disabled by rollout policy.",
    )


def _legacy_api_allowed() -> bool:
    allowed = get_rollout_config().legacy_shims_enabled
    if not allowed:
        logger.warning("Legacy shim call rejected by rollout policy.")
    return allowed


# Legacy function names kept for compatibility.
def execute_search(query: str, limit: int = 5):
    if not _legacy_api_allowed():
        return _legacy_disabled_response("execute_search")
    return search_archive(query=query, limit=limit)


def execute_metadata_lookup(identifier: str):
    if not _legacy_api_allowed():
        return _legacy_disabled_response("execute_metadata_lookup")
    return get_archive_metadata(identifier=identifier)


def execute_download(
    identifier: str,
    filename: str,
    destination_dir: str = "",
    destination_filename: str | None = None,
    overwrite: bool = False,
):
    if not _legacy_api_allowed():
        return _legacy_disabled_response("execute_download")
    return download_archive_file(
        identifier=identifier,
        filename=filename,
        destination_dir=destination_dir,
        destination_filename=destination_filename,
        overwrite=overwrite,
    )


__all__ = [
    "set_archive_session",
    "search_archive",
    "get_archive_metadata",
    "download_archive_file",
    "execute_search",
    "execute_metadata_lookup",
    "execute_download",
]
