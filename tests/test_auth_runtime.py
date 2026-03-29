from __future__ import annotations

import os

from percival_internetarchive_mcp import auth


def test_init_auth_returns_none_and_clears_partial_env(monkeypatch) -> None:
    monkeypatch.setenv("IA_ACCESS_KEY_ID", "only-access")
    monkeypatch.delenv("IA_SECRET_ACCESS_KEY", raising=False)

    session = auth.init_auth()

    assert session is None
    assert os.environ.get("IA_ACCESS_KEY_ID") is None
    assert os.environ.get("IA_SECRET_ACCESS_KEY") is None
    summary = auth.get_auth_state_summary()
    assert summary["mode"] == "anonymous"
    assert summary["reason"] == "partial_credentials"


def test_init_auth_builds_session_from_short_env_names(monkeypatch) -> None:
    captured: dict[str, object] = {}
    fake_session = object()

    def _fake_get_session(*, config):
        captured["config"] = config
        return fake_session

    monkeypatch.setenv("IA_ACCESS_KEY", "my-access")
    monkeypatch.setenv("IA_SECRET_KEY", "my-secret")
    monkeypatch.setattr(auth, "get_session", _fake_get_session)

    session = auth.init_auth()

    assert session is fake_session
    assert captured["config"] == {
        "s3": {
            "access": "my-access",
            "secret": "my-secret",
        }
    }
    assert os.environ["IA_ACCESS_KEY_ID"] == "my-access"
    assert os.environ["IA_SECRET_ACCESS_KEY"] == "my-secret"
    summary = auth.get_auth_state_summary()
    assert summary["mode"] == "authenticated"
    assert summary["reason"] == "ok"
    assert summary["credential_source"] == "short_env"
