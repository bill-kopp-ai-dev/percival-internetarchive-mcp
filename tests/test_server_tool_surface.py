from __future__ import annotations

import json

from percival_internetarchive_mcp import server


def test_get_archive_metadata_tool_uses_standard_envelope(monkeypatch) -> None:
    monkeypatch.setattr(
        server.archive_tools,
        "get_archive_metadata",
        lambda identifier: {
            "ok": True,
            "data": {"identifier": identifier, "files": []},
            "error": None,
            "meta": {"tool": "get_archive_metadata"},
        },
    )

    raw = server.get_archive_metadata("abc")
    payload = json.loads(raw)

    assert payload["ok"] is True
    assert payload["data"]["identifier"] == "abc"
    assert payload["meta"]["tool"] == "get_archive_metadata"
    assert "request_id" in payload["meta"]
    assert "duration_ms" in payload["meta"]


def test_download_archive_file_tool_passes_destination_arguments(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_download_archive_file(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "data": {"path": "/tmp/final.txt"},
            "error": None,
            "meta": {"tool": "download_archive_file"},
        }

    monkeypatch.setattr(
        server.archive_tools,
        "download_archive_file",
        _fake_download_archive_file,
    )

    raw = server.download_archive_file(
        "demo-item",
        "demo.txt",
        "/tmp",
        "final.txt",
        True,
    )
    payload = json.loads(raw)

    assert payload["ok"] is True
    assert captured == {
        "identifier": "demo-item",
        "filename": "demo.txt",
        "destination_dir": "/tmp",
        "destination_filename": "final.txt",
        "overwrite": True,
    }


def test_get_server_status_returns_metrics_and_governance() -> None:
    raw = server.get_server_status()
    payload = json.loads(raw)

    assert payload["ok"] is True
    data = payload["data"]
    assert data["server"]["name"] == "InternetArchive-MCP"
    assert "uptime_seconds" in data["server"]
    assert "metrics" in data
    assert "total_calls" in data["metrics"]
    assert "download_governance" in data
    assert "security_policy" in data
    assert "security_posture" in data
    assert "rollout" in data
    assert "rollout_runtime" in data
    assert "auth" in data


def test_reload_runtime_config_returns_runtime_snapshots() -> None:
    raw = server.reload_runtime_config()
    payload = json.loads(raw)

    assert payload["ok"] is True
    assert "security_policy" in payload["data"]
    assert "security_posture" in payload["data"]
    assert "auth" in payload["data"]
    assert "download_governance" in payload["data"]
    assert "rollout" in payload["data"]
    assert "rollout_runtime" in payload["data"]


def test_get_security_posture_tool_returns_envelope() -> None:
    raw = server.get_security_posture()
    payload = json.loads(raw)

    assert "ok" in payload
    if payload["ok"] is True:
        assert "compliant" in payload["data"]
    else:
        assert payload["error"]["code"] == "SECURITY_POSTURE_NON_COMPLIANT"
