from __future__ import annotations

import json
from pathlib import Path

import pytest

from percival_internetarchive_mcp import archive_tools, security_policy, server
from percival_internetarchive_mcp.contracts import error_response


@pytest.fixture(autouse=True)
def _reset_security_and_governance_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(security_policy.ENV_SECURITY_PROFILE, raising=False)
    monkeypatch.delenv(security_policy.ENV_DEBUG_ERROR_DETAILS, raising=False)
    monkeypatch.delenv(security_policy.ENV_LOG_EXCEPTION_DETAILS, raising=False)
    monkeypatch.delenv(security_policy.ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(security_policy.ENV_REQUIRE_AUTH, raising=False)
    monkeypatch.delenv(security_policy.ENV_MARK_UNTRUSTED_CONTENT, raising=False)
    monkeypatch.delenv(security_policy.ENV_SANITIZE_UNTRUSTED_TEXT, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_QUERY_LENGTH, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_IDENTIFIER_LENGTH, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_FILENAME_LENGTH, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_TEXT_FIELD_CHARS, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_METADATA_FIELDS, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_METADATA_LIST_ITEMS, raising=False)
    monkeypatch.delenv(security_policy.ENV_MAX_FILES_LIST, raising=False)
    monkeypatch.delenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_FORBIDDEN_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_MAX_DOWNLOAD_BYTES, raising=False)
    monkeypatch.delenv(archive_tools.ENV_DOWNLOAD_TIMEOUT_SECONDS, raising=False)
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    server.reload_runtime_config()
    yield
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    server.reload_runtime_config()


class _FakeFile:
    def download(self, **kwargs):
        target = Path(str(kwargs["destdir"])) / str(kwargs["file_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("demo", encoding="utf-8")
        return True


class _FakeItem:
    def __init__(self):
        self.exists = True
        self.metadata = {"identifier": "demo-item"}
        self.files = [{"name": "demo.txt", "size": "4"}]
        self.file = _FakeFile()

    def get_file(self, _name: str):
        return self.file


def test_prod_profile_requires_allowlist_and_hides_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    summary = security_policy.reload_security_policy_config()

    assert summary["profile"] == "prod"
    assert summary["require_allowed_download_dirs"] is True
    assert summary["debug_error_details"] is False
    assert summary["log_exception_details"] is False
    assert summary["require_auth"] is True


def test_download_is_fail_closed_when_prod_allowlist_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()

    called = {"get_item": False}

    def _should_not_be_called(*_args, **_kwargs):
        called["get_item"] = True
        raise AssertionError("get_item should not be called when policy is misconfigured")

    monkeypatch.setattr(archive_tools, "get_item", _should_not_be_called)

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir=str(tmp_path),
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "DESTINATION_POLICY_BLOCKED"
    assert security_policy.ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS in payload["error"]["message"] or (
        archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS in payload["error"]["message"]
    )
    assert called["get_item"] is False


def test_download_succeeds_in_prod_with_explicit_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    monkeypatch.setenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, str(tmp_path))
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    monkeypatch.setattr(archive_tools, "get_item", lambda *_a, **_k: _FakeItem())

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir=str(tmp_path),
    )

    assert payload["ok"] is True
    assert (tmp_path / "demo.txt").exists()


def test_server_redacts_error_details_when_debug_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    server.reload_runtime_config()

    monkeypatch.setattr(
        server.archive_tools,
        "search_archive",
        lambda **_kwargs: error_response(
            "search_archive",
            "SEARCH_FAILED",
            "Failed to search.",
            details="internal traceback-like detail",
        ),
    )

    payload = json.loads(server.search_archive("collection:test", 1))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SEARCH_FAILED"
    assert "details" not in payload["error"]


def test_server_keeps_error_details_when_debug_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "dev")
    monkeypatch.setenv(security_policy.ENV_DEBUG_ERROR_DETAILS, "true")
    server.reload_runtime_config()

    monkeypatch.setattr(
        server.archive_tools,
        "search_archive",
        lambda **_kwargs: error_response(
            "search_archive",
            "SEARCH_FAILED",
            "Failed to search.",
            details="internal traceback-like detail",
        ),
    )

    payload = json.loads(server.search_archive("collection:test", 1))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SEARCH_FAILED"
    assert payload["error"]["details"] == "internal traceback-like detail"


def test_reload_runtime_config_returns_auth_required_when_policy_needs_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    monkeypatch.delenv("IA_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IA_SECRET_KEY", raising=False)
    monkeypatch.delenv("IA_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("IA_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setattr(server, "ia_session", None)
    archive_tools.set_archive_session(None)

    payload = json.loads(server.reload_runtime_config())

    assert payload["ok"] is False
    assert payload["error"]["code"] == "AUTH_REQUIRED"
