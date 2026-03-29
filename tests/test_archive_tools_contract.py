from __future__ import annotations

from pathlib import Path

import pytest

from percival_internetarchive_mcp import archive_tools
from percival_internetarchive_mcp import security_policy


@pytest.fixture(autouse=True)
def _reload_governance_between_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_FORBIDDEN_DOWNLOAD_DIRS, raising=False)
    monkeypatch.delenv(archive_tools.ENV_MAX_DOWNLOAD_BYTES, raising=False)
    monkeypatch.delenv(archive_tools.ENV_DOWNLOAD_TIMEOUT_SECONDS, raising=False)
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
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()
    yield
    security_policy.reload_security_policy_config()
    archive_tools.reload_runtime_config()


def test_search_archive_returns_success_envelope(monkeypatch) -> None:
    fake_results = iter(
        [
            {
                "identifier": "item-1",
                "title": "Title 1",
                "mediatype": "texts",
                "date": "2024-01-01",
            },
            {
                "identifier": "item-2",
                "title": ["Title 2"],
                "mediatype": "movies",
                "date": "2023-01-01",
            },
        ]
    )

    def _fake_search_items(**kwargs):
        assert kwargs["query"] == "collection:test"
        return fake_results

    monkeypatch.setattr(archive_tools, "search_items", _fake_search_items)

    payload = archive_tools.search_archive("collection:test", limit=5)

    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["meta"]["tool"] == "search_archive"
    assert payload["meta"]["untrusted_content"] is True
    assert payload["meta"]["content_source"] == "internet_archive"
    assert "safe_handling" in payload["meta"]
    assert payload["data"]["count"] == 2
    assert payload["data"]["items"][0]["identifier"] == "item-1"


def test_search_archive_rejects_too_long_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(security_policy.ENV_MAX_QUERY_LENGTH, "8")
    security_policy.reload_security_policy_config()

    payload = archive_tools.search_archive("collection:test")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_QUERY_TOO_LONG"


def test_search_archive_hides_exception_details_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "prod")
    security_policy.reload_security_policy_config()

    def _raise_error(**_kwargs):
        raise RuntimeError("traceback-like internals")

    monkeypatch.setattr(archive_tools, "search_items", _raise_error)

    payload = archive_tools.search_archive("collection:test")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "SEARCH_FAILED"
    assert "details" not in payload["error"]


def test_search_archive_keeps_exception_details_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(security_policy.ENV_SECURITY_PROFILE, "dev")
    monkeypatch.setenv(security_policy.ENV_DEBUG_ERROR_DETAILS, "true")
    security_policy.reload_security_policy_config()

    def _raise_error(**_kwargs):
        raise RuntimeError("traceback-like internals")

    monkeypatch.setattr(archive_tools, "search_items", _raise_error)

    payload = archive_tools.search_archive("collection:test")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "SEARCH_FAILED"
    assert payload["error"]["details"] == "traceback-like internals"


def test_get_archive_metadata_rejects_empty_identifier() -> None:
    payload = archive_tools.get_archive_metadata("   ")

    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "INVALID_IDENTIFIER"


def test_get_archive_metadata_rejects_too_long_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(security_policy.ENV_MAX_IDENTIFIER_LENGTH, "5")
    security_policy.reload_security_policy_config()

    payload = archive_tools.get_archive_metadata("abcdefgh")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_IDENTIFIER_TOO_LONG"


class _FakeFile:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def download(self, **kwargs):
        self.calls.append(kwargs)
        target = Path(str(kwargs["destdir"])) / str(kwargs["file_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("demo", encoding="utf-8")
        return True


class _FakeItem:
    def __init__(self, exists: bool = True, size: int = 4):
        self.exists = exists
        self.metadata = {"identifier": "demo-item", "title": "Demo"}
        self.files = [{"name": "demo.txt", "size": str(size)}]
        self.file = _FakeFile()

    def get_file(self, name: str):
        assert name == "demo.txt"
        return self.file


def test_get_archive_metadata_applies_sanitization_and_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_MAX_METADATA_FIELDS, "1")
    monkeypatch.setenv(security_policy.ENV_MAX_METADATA_LIST_ITEMS, "1")
    monkeypatch.setenv(security_policy.ENV_MAX_FILES_LIST, "1")
    monkeypatch.setenv(security_policy.ENV_MAX_TEXT_FIELD_CHARS, "12")
    security_policy.reload_security_policy_config()

    item = _FakeItem()
    item.metadata = {
        "title": "Line1\nLine2 with very very long value",
        "description": "This field should be dropped by field limit",
        "subject": ["alpha", "beta"],
    }
    item.files = [
        {"name": "demo.txt", "size": "4"},
        {"name": "demo2.txt", "size": "4"},
    ]
    monkeypatch.setattr(archive_tools, "get_item", lambda *_args, **_kwargs: item)

    payload = archive_tools.get_archive_metadata("demo-item")

    assert payload["ok"] is True
    assert payload["meta"]["untrusted_content"] is True
    data = payload["data"]
    assert data["files_total"] == 2
    assert data["files_truncated"] is True
    assert len(data["files"]) == 1
    assert data["limits"]["metadata_total_fields"] == 3
    assert data["limits"]["metadata_returned_fields"] == 1
    assert data["limits"]["metadata_truncated"] is True
    # Newline should be normalized and long text should be truncated.
    metadata_value = next(iter(data["metadata"].values()))
    assert isinstance(metadata_value, str)
    assert "\n" not in metadata_value
    assert metadata_value.endswith("...")


def test_download_archive_file_writes_directly_to_selected_destination(
    monkeypatch, tmp_path: Path
) -> None:
    item = _FakeItem()
    monkeypatch.setattr(archive_tools, "get_item", lambda *_args, **_kwargs: item)

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir=str(tmp_path),
        destination_filename="final.txt",
    )

    target = tmp_path.resolve() / "final.txt"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["meta"]["tool"] == "download_archive_file"
    assert payload["data"]["path"] == str(target)
    assert payload["data"]["destination_filename"] == "final.txt"
    assert target.exists()
    assert not (tmp_path / "demo-item" / "demo.txt").exists()

    assert item.file.calls
    first_call = item.file.calls[0]
    assert first_call["file_path"] == "final.txt"
    assert first_call["destdir"] == str(tmp_path.resolve())


def test_download_archive_file_rejects_empty_destination_dir() -> None:
    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir="",
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_DESTINATION"


def test_download_archive_file_rejects_too_long_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(security_policy.ENV_MAX_FILENAME_LENGTH, "5")
    security_policy.reload_security_policy_config()

    payload = archive_tools.download_archive_file(
        "demo-item",
        "very-long-name.txt",
        destination_dir="/tmp",
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_FILENAME_TOO_LONG"


def test_download_archive_file_rejects_path_destination_filename(monkeypatch) -> None:
    monkeypatch.setattr(archive_tools, "get_item", lambda *_args, **_kwargs: _FakeItem())

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir="/tmp",
        destination_filename="nested/final.txt",
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_DESTINATION"


def test_download_archive_file_blocks_destination_outside_allowed_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    allowed_dir = tmp_path / "allowed"
    blocked_dir = tmp_path / "blocked"
    monkeypatch.setenv(archive_tools.ENV_ALLOWED_DOWNLOAD_DIRS, str(allowed_dir))
    archive_tools.reload_runtime_config()

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir=str(blocked_dir),
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "DESTINATION_POLICY_BLOCKED"


def test_download_archive_file_honors_max_download_bytes_precheck(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(archive_tools.ENV_MAX_DOWNLOAD_BYTES, "3")
    archive_tools.reload_runtime_config()

    item = _FakeItem(size=10)
    monkeypatch.setattr(archive_tools, "get_item", lambda *_args, **_kwargs: item)

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir=str(tmp_path),
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "FILE_TOO_LARGE"
    assert not item.file.calls


def test_download_governance_summary_is_serializable() -> None:
    summary = archive_tools.get_download_governance_summary()

    assert "allowed_dirs" in summary
    assert "allowlist_configured" in summary
    assert "allowlist_required" in summary
    assert "forbidden_dirs" in summary
    assert "max_download_bytes" in summary
    assert "timeout_seconds" in summary
