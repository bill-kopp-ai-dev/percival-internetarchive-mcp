from __future__ import annotations

import json
from pathlib import Path

import pytest

from percival_internetarchive_mcp import archive_tools, rollout, security_policy, server


@pytest.fixture(autouse=True)
def _reset_runtime_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(security_policy.ENV_SECURITY_PROFILE, raising=False)
    monkeypatch.delenv(security_policy.ENV_DEBUG_ERROR_DETAILS, raising=False)
    monkeypatch.delenv(security_policy.ENV_LOG_EXCEPTION_DETAILS, raising=False)
    monkeypatch.delenv(security_policy.ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(security_policy.ENV_REQUIRE_AUTH, raising=False)
    monkeypatch.delenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_FORBIDDEN_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_MAX_DOWNLOAD_BYTES, raising=False)
    monkeypatch.delenv(archive_tools.ENV_DOWNLOAD_TIMEOUT_SECONDS, raising=False)
    monkeypatch.delenv(rollout.ENV_ROLLOUT_PHASE, raising=False)
    monkeypatch.delenv(rollout.ENV_COMPAT_RESOURCE_ENABLED, raising=False)
    monkeypatch.delenv(rollout.ENV_LEGACY_SHIMS_ENABLED, raising=False)
    monkeypatch.delenv(rollout.ENV_ALLOW_EMPTY_DESTINATION, raising=False)
    monkeypatch.delenv(rollout.ENV_DEFAULT_DOWNLOAD_DIR, raising=False)
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    rollout.reload_rollout_config()
    server.ia_session = None
    archive_tools.set_archive_session(None)
    server.reload_runtime_config()
    yield
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    rollout.reload_rollout_config()
    server.ia_session = None
    archive_tools.set_archive_session(None)
    server.reload_runtime_config()


def test_reload_runtime_config_blocks_phase2_when_security_posture_is_non_compliant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")

    payload = json.loads(server.reload_runtime_config())

    assert payload["ok"] is False
    assert payload["error"]["code"] == "SECURITY_POSTURE_NON_COMPLIANT"
    assert "phase2_strict_profile" in payload["meta"]["failed_checks"]


def test_get_security_posture_reports_non_compliance_in_phase2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")
    server.reload_runtime_config()

    payload = json.loads(server.get_security_posture())

    assert payload["ok"] is False
    assert payload["error"]["code"] == "SECURITY_POSTURE_NON_COMPLIANT"
    assert payload["meta"]["phase"] == "phase2"
    assert "failed_checks" in payload["meta"]


def test_phase2_with_prod_profile_and_auth_and_allowlist_is_compliant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    monkeypatch.setenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, str(tmp_path))
    server.ia_session = object()
    archive_tools.set_archive_session(server.ia_session)

    reload_payload = json.loads(server.reload_runtime_config())
    posture_payload = json.loads(server.get_security_posture())

    assert reload_payload["ok"] is True
    assert reload_payload["data"]["security_posture"]["compliant"] is True
    assert posture_payload["ok"] is True
    assert posture_payload["data"]["compliant"] is True
