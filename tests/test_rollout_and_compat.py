from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from percival_internetarchive_mcp import archive_tools, rollout


@pytest.fixture(autouse=True)
def _reload_runtime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(rollout.ENV_ROLLOUT_PHASE, raising=False)
    monkeypatch.delenv(rollout.ENV_COMPAT_RESOURCE_ENABLED, raising=False)
    monkeypatch.delenv(rollout.ENV_LEGACY_SHIMS_ENABLED, raising=False)
    monkeypatch.delenv(rollout.ENV_ALLOW_EMPTY_DESTINATION, raising=False)
    monkeypatch.delenv(rollout.ENV_DEFAULT_DOWNLOAD_DIR, raising=False)
    rollout.reload_rollout_config()
    archive_tools.reload_runtime_config()
    yield
    rollout.reload_rollout_config()
    archive_tools.reload_runtime_config()


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


def test_rollout_phase2_disables_legacy_shims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")
    rollout.reload_rollout_config()

    tools_path = Path(__file__).resolve().parents[1] / "tools.py"
    spec = importlib.util.spec_from_file_location("legacy_tools_shim", tools_path)
    assert spec is not None
    assert spec.loader is not None
    legacy_tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_tools)
    payload = legacy_tools.execute_search("collection:test")

    assert payload["ok"] is False
    assert payload["error"]["code"] == "LEGACY_API_DISABLED"


def test_rollout_phase2_blocks_legacy_auth_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")
    rollout.reload_rollout_config()

    auth_path = Path(__file__).resolve().parents[1] / "auth.py"
    spec = importlib.util.spec_from_file_location("legacy_auth_shim", auth_path)
    assert spec is not None
    assert spec.loader is not None
    legacy_auth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_auth)

    with pytest.raises(RuntimeError):
        legacy_auth.init_auth()


def test_rollout_phase2_blocks_legacy_bootstrap_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase2")
    rollout.reload_rollout_config()

    bootstrap_path = Path(__file__).resolve().parents[1] / "ia_bootstrap.py"
    spec = importlib.util.spec_from_file_location("legacy_bootstrap_shim", bootstrap_path)
    assert spec is not None
    assert spec.loader is not None
    legacy_bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_bootstrap)

    with pytest.raises(RuntimeError):
        legacy_bootstrap.ensure_internetarchive_import_path()


def test_download_can_use_rollout_default_destination_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase0")
    monkeypatch.setenv(rollout.ENV_DEFAULT_DOWNLOAD_DIR, str(tmp_path))
    rollout.reload_rollout_config()

    monkeypatch.setattr(archive_tools, "get_item", lambda *_a, **_k: _FakeItem())

    payload = archive_tools.download_archive_file(
        "demo-item",
        "demo.txt",
        destination_dir="",
    )

    assert payload["ok"] is True
    assert payload["data"]["destination_source"] == "rollout_default"
    assert (tmp_path / "demo.txt").exists()


def test_rollout_override_for_compat_resource_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(rollout.ENV_ROLLOUT_PHASE, "phase1")
    monkeypatch.setenv(rollout.ENV_COMPAT_RESOURCE_ENABLED, "false")

    summary = rollout.reload_rollout_config()

    assert summary["phase"] == "phase1"
    assert summary["compat_resource_enabled"] is False
