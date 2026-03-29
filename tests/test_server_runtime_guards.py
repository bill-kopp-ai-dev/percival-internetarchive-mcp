from __future__ import annotations

import json

from percival_internetarchive_mcp import server


def test_search_archive_wraps_non_dict_handler_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        server.archive_tools,
        "search_archive",
        lambda **_kwargs: ["invalid"],
    )

    raw = server.search_archive("collection:test", 1)
    payload = json.loads(raw)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_HANDLER_PAYLOAD"


def test_search_archive_wraps_unhandled_exception(monkeypatch) -> None:
    def _raise_error(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(server.archive_tools, "search_archive", _raise_error)

    raw = server.search_archive("collection:test", 1)
    payload = json.loads(raw)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNHANDLED_EXCEPTION"
