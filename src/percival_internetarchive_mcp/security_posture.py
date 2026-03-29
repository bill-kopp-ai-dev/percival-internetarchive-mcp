from __future__ import annotations

from typing import Any


STRICT_SECURITY_PROFILES = {"staging", "prod"}


def _as_bool(value: Any) -> bool:
    return bool(value)


def _failed_check_ids(checks: list[dict[str, Any]]) -> list[str]:
    return [
        str(check.get("id"))
        for check in checks
        if not _as_bool(check.get("ok"))
    ]


def evaluate_security_posture(
    *,
    security_policy: dict[str, Any],
    rollout: dict[str, Any],
    download_governance: dict[str, Any],
    auth: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate runtime security posture from normalized snapshots.

    Input snapshots are expected to come from:
    - `get_security_policy_summary()`
    - `get_rollout_summary()`
    - `get_download_governance_summary()`
    - server auth payload (`authenticated_session`, `compliant`, etc.)

    Returns:
        Dict with top-level compliance flag plus per-check diagnostics
        (`checks`, `failed_checks`, `error_count`, `warning_count`).
    """

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, severity: str, message: str) -> None:
        checks.append(
            {
                "id": check_id,
                "ok": ok,
                "severity": severity,
                "message": message,
            }
        )

    profile = str(security_policy.get("profile", "dev"))
    phase = str(rollout.get("phase", "phase1"))

    require_auth = _as_bool(security_policy.get("require_auth"))
    require_allowlist = _as_bool(security_policy.get("require_allowed_download_dirs"))
    debug_error_details = _as_bool(security_policy.get("debug_error_details"))
    log_exception_details = _as_bool(security_policy.get("log_exception_details"))
    allowlist_configured = _as_bool(download_governance.get("allowlist_configured"))
    auth_compliant = _as_bool(auth.get("compliant"))

    add_check(
        "auth_required_compliant",
        (not require_auth) or auth_compliant,
        "error",
        "Authentication must be compliant when required by security policy.",
    )
    add_check(
        "allowlist_required_configured",
        (not require_allowlist) or allowlist_configured,
        "error",
        "Allowed download directories must be configured when required by security policy.",
    )
    add_check(
        "strict_profile_redacts_error_details",
        (profile not in STRICT_SECURITY_PROFILES) or (not debug_error_details),
        "error",
        "Strict security profiles must disable debug error details.",
    )
    add_check(
        "strict_profile_suppresses_exception_details",
        (profile not in STRICT_SECURITY_PROFILES) or (not log_exception_details),
        "error",
        "Strict security profiles must suppress detailed exception logging.",
    )
    add_check(
        "phase2_strict_profile",
        (phase != "phase2") or (profile in STRICT_SECURITY_PROFILES),
        "error",
        "Rollout phase2 requires staging/prod security profile.",
    )
    add_check(
        "phase2_legacy_shims_disabled",
        (phase != "phase2") or (not _as_bool(rollout.get("legacy_shims_enabled"))),
        "error",
        "Rollout phase2 requires legacy shims to be disabled.",
    )
    add_check(
        "phase2_compat_resource_disabled",
        (phase != "phase2") or (not _as_bool(rollout.get("compat_resource_enabled"))),
        "error",
        "Rollout phase2 requires compatibility resource to be disabled.",
    )
    add_check(
        "phase2_explicit_destination_required",
        (phase != "phase2") or (not _as_bool(rollout.get("allow_empty_destination"))),
        "error",
        "Rollout phase2 requires explicit destination directory usage.",
    )
    add_check(
        "phase2_auth_policy_required",
        (phase != "phase2") or require_auth,
        "error",
        "Rollout phase2 requires authentication policy to be enabled.",
    )
    add_check(
        "phase2_allowlist_policy_required",
        (phase != "phase2") or require_allowlist,
        "error",
        "Rollout phase2 requires download allowlist policy enforcement.",
    )

    failed_checks = _failed_check_ids(checks)
    error_count = sum(1 for check in checks if (not check["ok"]) and check["severity"] == "error")
    warning_count = sum(1 for check in checks if (not check["ok"]) and check["severity"] == "warning")

    return {
        "phase": phase,
        "profile": profile,
        "compliant": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "failed_checks": failed_checks,
        "checks": checks,
    }
