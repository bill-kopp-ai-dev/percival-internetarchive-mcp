from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ENV_ROLLOUT_PHASE = "IA_MCP_ROLLOUT_PHASE"
ENV_COMPAT_RESOURCE_ENABLED = "IA_MCP_COMPAT_RESOURCE_ENABLED"
ENV_LEGACY_SHIMS_ENABLED = "IA_MCP_LEGACY_SHIMS_ENABLED"
ENV_ALLOW_EMPTY_DESTINATION = "IA_MCP_ALLOW_EMPTY_DESTINATION"
ENV_DEFAULT_DOWNLOAD_DIR = "IA_MCP_DEFAULT_DOWNLOAD_DIR"

DEFAULT_ROLLOUT_PHASE = "phase1"
VALID_ROLLOUT_PHASES = {"phase0", "phase1", "phase2"}

NANOBOT_CONTRACT_VERSION = "v1"


@dataclass(frozen=True)
class RolloutConfig:
    phase: str
    compat_resource_enabled: bool
    legacy_shims_enabled: bool
    allow_empty_destination: bool
    default_download_dir: str | None


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_phase(raw_phase: str) -> str:
    phase = (raw_phase or "").strip().lower()
    if phase in VALID_ROLLOUT_PHASES:
        return phase
    return DEFAULT_ROLLOUT_PHASE


def _phase_defaults(phase: str) -> dict[str, bool]:
    if phase == "phase0":
        return {
            "compat_resource_enabled": True,
            "legacy_shims_enabled": True,
            "allow_empty_destination": True,
        }
    if phase == "phase2":
        return {
            "compat_resource_enabled": False,
            "legacy_shims_enabled": False,
            "allow_empty_destination": False,
        }
    return {
        "compat_resource_enabled": True,
        "legacy_shims_enabled": True,
        "allow_empty_destination": False,
    }


def _normalize_default_download_dir(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return str(Path(stripped).expanduser().resolve(strict=False))


def _load_rollout_config_from_env() -> RolloutConfig:
    phase = _normalize_phase(os.getenv(ENV_ROLLOUT_PHASE, DEFAULT_ROLLOUT_PHASE))
    defaults = _phase_defaults(phase)
    return RolloutConfig(
        phase=phase,
        compat_resource_enabled=_parse_bool_env(
            ENV_COMPAT_RESOURCE_ENABLED,
            defaults["compat_resource_enabled"],
        ),
        legacy_shims_enabled=_parse_bool_env(
            ENV_LEGACY_SHIMS_ENABLED,
            defaults["legacy_shims_enabled"],
        ),
        allow_empty_destination=_parse_bool_env(
            ENV_ALLOW_EMPTY_DESTINATION,
            defaults["allow_empty_destination"],
        ),
        default_download_dir=_normalize_default_download_dir(
            os.getenv(ENV_DEFAULT_DOWNLOAD_DIR),
        ),
    )


_rollout_config: RolloutConfig = _load_rollout_config_from_env()


def reload_rollout_config() -> dict[str, Any]:
    global _rollout_config
    _rollout_config = _load_rollout_config_from_env()
    return get_rollout_summary()


def get_rollout_config() -> RolloutConfig:
    return _rollout_config


def get_rollout_summary() -> dict[str, Any]:
    config = _rollout_config
    return {
        "phase": config.phase,
        "nanobot_contract_version": NANOBOT_CONTRACT_VERSION,
        "compat_resource_enabled": config.compat_resource_enabled,
        "legacy_shims_enabled": config.legacy_shims_enabled,
        "allow_empty_destination": config.allow_empty_destination,
        "default_download_dir": config.default_download_dir,
        "env": {
            "phase": ENV_ROLLOUT_PHASE,
            "compat_resource_enabled": ENV_COMPAT_RESOURCE_ENABLED,
            "legacy_shims_enabled": ENV_LEGACY_SHIMS_ENABLED,
            "allow_empty_destination": ENV_ALLOW_EMPTY_DESTINATION,
            "default_download_dir": ENV_DEFAULT_DOWNLOAD_DIR,
        },
    }
