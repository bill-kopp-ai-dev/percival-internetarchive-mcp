from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any

from fastmcp import FastMCP

from .auth import get_auth_state_summary, init_auth
from . import archive_tools
from .contracts import error_response, success_response
from .observability import TelemetryRegistry
from .rollout import get_rollout_config, get_rollout_summary, reload_rollout_config
from .security_posture import evaluate_security_posture
from .security_policy import (
    get_security_policy_config,
    get_security_policy_summary,
    reload_security_policy_config,
)


LOG_LEVEL_NAME = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize auth/session before registering tools.
ia_session = init_auth()
archive_tools.set_archive_session(ia_session)
startup_rollout = get_rollout_config()
startup_policy = get_security_policy_config()
if startup_policy.require_auth and ia_session is None:
    auth_summary = get_auth_state_summary()
    raise RuntimeError(
        "IA authentication is required by security policy profile "
        f"'{startup_policy.profile}' but was not initialized "
        f"(auth_reason={auth_summary.get('reason', 'unknown')})."
    )
startup_auth_summary = get_auth_state_summary()
startup_auth_payload = {
    "authenticated_session": ia_session is not None,
    "required_by_policy": startup_policy.require_auth,
    "compliant": (not startup_policy.require_auth) or (ia_session is not None),
    **startup_auth_summary,
}
startup_security_posture = evaluate_security_posture(
    security_policy=get_security_policy_summary(),
    rollout=get_rollout_summary(),
    download_governance=archive_tools.get_download_governance_summary(),
    auth=startup_auth_payload,
)
if startup_rollout.phase == "phase2" and (not startup_security_posture["compliant"]):
    failed_checks = ", ".join(startup_security_posture["failed_checks"]) or "unknown"
    raise RuntimeError(
        "Rollout phase2 startup blocked due to non-compliant security posture: "
        f"{failed_checks}"
    )

# Initialize MCP server and telemetry.
mcp = FastMCP(name="InternetArchive-MCP")
telemetry = TelemetryRegistry(server_name="InternetArchive-MCP")


def _to_json(payload: dict) -> str:
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False, sort_keys=True)


def _extract_error_code(payload: dict[str, Any]) -> str | None:
    error_obj = payload.get("error")
    if isinstance(error_obj, dict):
        code = error_obj.get("code")
        if isinstance(code, str) and code:
            return code
    return None


def _apply_error_detail_policy(payload: dict[str, Any]) -> None:
    if get_security_policy_config().debug_error_details:
        return

    error_obj = payload.get("error")
    if isinstance(error_obj, dict):
        error_obj.pop("details", None)


def _run_observed(tool_name: str, fn, **kwargs: Any) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    started = time.perf_counter()

    try:
        payload = fn(**kwargs)
        if not isinstance(payload, dict):
            payload = error_response(
                tool_name,
                "INVALID_HANDLER_PAYLOAD",
                "Handler returned a non-dict payload.",
            )
    except Exception as exc:
        policy = get_security_policy_config()
        if policy.log_exception_details:
            logger.exception("Unhandled error in tool '%s': %s", tool_name, exc)
        else:
            logger.error("Unhandled error in tool '%s'.", tool_name)
        payload = error_response(
            tool_name,
            "UNHANDLED_EXCEPTION",
            "Unhandled exception while executing tool.",
            details=str(exc) if policy.debug_error_details else None,
        )

    _apply_error_detail_policy(payload)

    duration_ms = (time.perf_counter() - started) * 1000.0
    ok = bool(payload.get("ok"))
    error_code = _extract_error_code(payload)

    telemetry.record(
        tool_name,
        duration_ms=duration_ms,
        ok=ok,
        error_code=error_code,
    )

    payload_meta = payload.setdefault("meta", {})
    payload_meta.setdefault("tool", tool_name)
    payload_meta["request_id"] = request_id
    payload_meta["duration_ms"] = round(duration_ms, 3)

    if ok:
        logger.info(
            "mcp_call tool=%s request_id=%s ok=true duration_ms=%.3f",
            tool_name,
            request_id,
            duration_ms,
        )
    else:
        logger.warning(
            "mcp_call tool=%s request_id=%s ok=false duration_ms=%.3f error_code=%s",
            tool_name,
            request_id,
            duration_ms,
            error_code or "UNKNOWN",
        )

    return payload


def _build_runtime_snapshots() -> dict[str, Any]:
    policy = get_security_policy_config()
    auth_summary = get_auth_state_summary()
    auth = {
        "authenticated_session": ia_session is not None,
        "required_by_policy": policy.require_auth,
        "compliant": (not policy.require_auth) or (ia_session is not None),
        **auth_summary,
    }
    security_policy = get_security_policy_summary()
    rollout = get_rollout_summary()
    download_governance = archive_tools.get_download_governance_summary()
    security_posture = evaluate_security_posture(
        security_policy=security_policy,
        rollout=rollout,
        download_governance=download_governance,
        auth=auth,
    )
    return {
        "auth": auth,
        "security_policy": security_policy,
        "rollout": rollout,
        "download_governance": download_governance,
        "security_posture": security_posture,
    }


def archive_metadata_resource(identifier: str) -> str:
    """Compatibility resource that proxies `get_archive_metadata`.

    This resource exists for migration support and returns the same JSON
    envelope contract used by tools (`ok`, `data`, `error`, `meta`).
    """
    payload = _run_observed(
        "archive_metadata_resource",
        archive_tools.get_archive_metadata,
        identifier=identifier,
    )
    return _to_json(payload)

COMPAT_RESOURCE_REGISTERED = startup_rollout.compat_resource_enabled
if COMPAT_RESOURCE_REGISTERED:
    mcp.resource("archive://{identifier}/metadata")(archive_metadata_resource)


@mcp.tool()
def search_archive(query: str, limit: int = 5) -> str:
    """Search Internet Archive and return compact item records.

    Args:
        query: Search expression used by Internet Archive.
        limit: Desired max result count. Runtime clamps this value to an
            allowed range for safety.

    Returns:
        JSON string envelope with:
        - `data.items`: list of `{identifier, title, mediatype, date}`
        - `data.count`: number of returned items
        - `meta.request_id` and `meta.duration_ms`

    Error codes:
        `INVALID_QUERY`, `INVALID_QUERY_TOO_LONG`, `SEARCH_FAILED`.
    """
    payload = _run_observed(
        "search_archive",
        archive_tools.search_archive,
        query=query,
        limit=limit,
    )
    return _to_json(payload)


@mcp.tool()
def get_archive_metadata(identifier: str) -> str:
    """Get metadata and file list for one Internet Archive identifier.

    Args:
        identifier: Archive item identifier.

    Returns:
        JSON string envelope with:
        - `data.metadata`: sanitized/truncated metadata dictionary
        - `data.files`: bounded list of available file names
        - `data.limits`: truncation/limit counters for robust client handling

    Error codes:
        `INVALID_IDENTIFIER`, `INVALID_IDENTIFIER_TOO_LONG`,
        `ITEM_NOT_FOUND`, `METADATA_LOOKUP_FAILED`.
    """
    payload = _run_observed(
        "get_archive_metadata",
        archive_tools.get_archive_metadata,
        identifier=identifier,
    )
    return _to_json(payload)


@mcp.tool()
def download_archive_file(
    identifier: str,
    filename: str,
    destination_dir: str,
    destination_filename: str = "",
    overwrite: bool = False,
) -> str:
    """Download one Archive file directly to caller destination.

    Args:
        identifier: Archive item identifier.
        filename: Exact source file name inside the item.
        destination_dir: Final target directory. Empty only works when rollout
            explicitly allows fallback destination behavior.
        destination_filename: Optional output file name override.
        overwrite: When true, replace existing target file.

    Returns:
        JSON string envelope with:
        - `data.path`: final absolute/normalized target path
        - `data.size_bytes`: downloaded file size
        - `data.destination_source`: `explicit` or `rollout_default`

    Error codes:
        `INVALID_IDENTIFIER`, `INVALID_FILENAME`, `INVALID_DESTINATION`,
        `DESTINATION_POLICY_BLOCKED`, `ITEM_NOT_FOUND`, `FILE_NOT_FOUND`,
        `TARGET_EXISTS`, `DOWNLOAD_FAILED`, `UNEXPECTED_ERROR`.
    """
    payload = _run_observed(
        "download_archive_file",
        archive_tools.download_archive_file,
        identifier=identifier,
        filename=filename,
        destination_dir=destination_dir,
        destination_filename=destination_filename or None,
        overwrite=overwrite,
    )
    return _to_json(payload)


@mcp.tool()
def get_server_status() -> str:
    """Return runtime health snapshot for orchestration and diagnostics.

    Returns a JSON string envelope with server telemetry and active runtime
    controls, including:
    - auth state and policy compliance
    - download governance config
    - security policy and evaluated security posture
    - rollout configuration and runtime flags
    """

    def _status_payload() -> dict[str, Any]:
        snapshots = _build_runtime_snapshots()
        return success_response(
            "get_server_status",
            telemetry.snapshot(
                auth=snapshots["auth"],
                download_governance=snapshots["download_governance"],
                security_policy=snapshots["security_policy"],
                security_posture=snapshots["security_posture"],
                rollout=snapshots["rollout"],
                rollout_runtime={
                    "compat_resource_registered": COMPAT_RESOURCE_REGISTERED,
                },
                logging={
                    "level": LOG_LEVEL_NAME,
                },
            ),
        )

    payload = _run_observed("get_server_status", _status_payload)
    return _to_json(payload)


@mcp.tool()
def reload_runtime_config() -> str:
    """Reload environment-driven runtime config and re-evaluate compliance.

    This refreshes security policy, download governance and rollout flags.
    It can return hard errors when policy enforcement fails.

    Error codes:
        `AUTH_REQUIRED` when auth is required but unavailable.
        `SECURITY_POSTURE_NON_COMPLIANT` when rollout `phase2` requires
        strict posture checks that are not satisfied.
    """

    def _reload_payload() -> dict[str, Any]:
        global ia_session
        reload_security_policy_config()
        policy = get_security_policy_config()

        if policy.require_auth and ia_session is None:
            refreshed_session = init_auth()
            if refreshed_session is not None:
                ia_session = refreshed_session
                archive_tools.set_archive_session(ia_session)

        auth_compliant = (not policy.require_auth) or (ia_session is not None)
        if not auth_compliant:
            auth_summary = get_auth_state_summary()
            return error_response(
                "reload_runtime_config",
                "AUTH_REQUIRED",
                "Security policy requires Internet Archive authentication.",
                profile=policy.profile,
                auth_reason=auth_summary.get("reason"),
            )

        archive_tools.reload_runtime_config()
        reload_rollout_config()
        snapshots = _build_runtime_snapshots()
        security_posture = snapshots["security_posture"]

        if snapshots["rollout"]["phase"] == "phase2" and (not security_posture["compliant"]):
            return error_response(
                "reload_runtime_config",
                "SECURITY_POSTURE_NON_COMPLIANT",
                "Rollout phase2 requires a compliant runtime security posture.",
                phase=security_posture["phase"],
                profile=security_posture["profile"],
                failed_checks=security_posture["failed_checks"],
                security_posture=security_posture,
            )

        return success_response(
            "reload_runtime_config",
            {
                "security_policy": snapshots["security_policy"],
                "security_posture": snapshots["security_posture"],
                "download_governance": snapshots["download_governance"],
                "rollout": snapshots["rollout"],
                "rollout_runtime": {
                    "compat_resource_registered": COMPAT_RESOURCE_REGISTERED,
                },
                "auth": snapshots["auth"],
            },
        )

    payload = _run_observed("reload_runtime_config", _reload_payload)
    return _to_json(payload)


@mcp.tool()
def get_security_posture() -> str:
    """Return evaluated runtime security posture checks.

    This tool is intended for preflight gating before canary/production
    rollout changes. It returns check-level compliance details.

    Error code:
        `SECURITY_POSTURE_NON_COMPLIANT` when one or more required checks fail.
    """

    def _security_posture_payload() -> dict[str, Any]:
        snapshots = _build_runtime_snapshots()
        posture = snapshots["security_posture"]
        if posture["compliant"]:
            return success_response("get_security_posture", posture)
        return error_response(
            "get_security_posture",
            "SECURITY_POSTURE_NON_COMPLIANT",
            "Runtime security posture is not compliant.",
            phase=posture["phase"],
            profile=posture["profile"],
            failed_checks=posture["failed_checks"],
            security_posture=posture,
        )

    payload = _run_observed("get_security_posture", _security_posture_payload)
    return _to_json(payload)


def main() -> None:
    mcp.run(transport="stdio")
