from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Optional

from .ia_bootstrap import ensure_internetarchive_import_path
from .security_policy import get_security_policy_config

ensure_internetarchive_import_path()

from internetarchive import get_session
from internetarchive.session import ArchiveSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthState:
    mode: str
    reason: str
    credential_source: str
    has_access_key: bool
    has_secret_key: bool


_auth_state = AuthState(
    mode="anonymous",
    reason="startup",
    credential_source="none",
    has_access_key=False,
    has_secret_key=False,
)


def _set_auth_state(
    *,
    mode: str,
    reason: str,
    credential_source: str,
    has_access_key: bool,
    has_secret_key: bool,
) -> None:
    global _auth_state
    _auth_state = AuthState(
        mode=mode,
        reason=reason,
        credential_source=credential_source,
        has_access_key=has_access_key,
        has_secret_key=has_secret_key,
    )


def _resolve_credentials() -> tuple[Optional[str], Optional[str], str]:
    access_short = os.environ.get("IA_ACCESS_KEY")
    secret_short = os.environ.get("IA_SECRET_KEY")
    access_long = os.environ.get("IA_ACCESS_KEY_ID")
    secret_long = os.environ.get("IA_SECRET_ACCESS_KEY")

    access_key = access_short or access_long
    secret_key = secret_short or secret_long

    if access_short and secret_short:
        source = "short_env"
    elif access_long and secret_long:
        source = "long_env"
    elif access_key or secret_key:
        source = "mixed_env"
    else:
        source = "none"
    return access_key, secret_key, source


def get_auth_state_summary() -> dict[str, object]:
    state = _auth_state
    return {
        "mode": state.mode,
        "reason": state.reason,
        "credential_source": state.credential_source,
        "has_access_key": state.has_access_key,
        "has_secret_key": state.has_secret_key,
    }


def init_auth() -> Optional[ArchiveSession]:
    """Initialize IA session from environment credentials.

    Accepted env pairs:
    - `IA_ACCESS_KEY` + `IA_SECRET_KEY`
    - `IA_ACCESS_KEY_ID` + `IA_SECRET_ACCESS_KEY`

    Returns:
        Authenticated `ArchiveSession` on success, otherwise `None` (anonymous
        mode with structured auth state reasons).
    """
    access_key, secret_key, credential_source = _resolve_credentials()
    has_access_key = bool(access_key)
    has_secret_key = bool(secret_key)

    if not has_access_key or not has_secret_key:
        # Avoid partial env state that can trigger ValueError in upstream config handling.
        os.environ.pop("IA_ACCESS_KEY_ID", None)
        os.environ.pop("IA_SECRET_ACCESS_KEY", None)
        reason = "partial_credentials" if (has_access_key or has_secret_key) else "missing_credentials"
        _set_auth_state(
            mode="anonymous",
            reason=reason,
            credential_source=credential_source,
            has_access_key=has_access_key,
            has_secret_key=has_secret_key,
        )
        logger.warning(
            "IA authentication not initialized (%s). Set IA_ACCESS_KEY/IA_SECRET_KEY or IA_ACCESS_KEY_ID/IA_SECRET_ACCESS_KEY.",
            reason,
        )
        return None

    os.environ["IA_ACCESS_KEY_ID"] = access_key
    os.environ["IA_SECRET_ACCESS_KEY"] = secret_key

    ia_config = {
        "s3": {
            "access": access_key,
            "secret": secret_key,
        }
    }

    try:
        session = get_session(config=ia_config)
    except Exception as exc:
        # Avoid leaking details unless explicitly enabled by policy.
        policy = get_security_policy_config()
        if policy.log_exception_details:
            logger.exception("IA authentication initialization failed: %s", exc)
        else:
            logger.error("IA authentication initialization failed.")
        os.environ.pop("IA_ACCESS_KEY_ID", None)
        os.environ.pop("IA_SECRET_ACCESS_KEY", None)
        _set_auth_state(
            mode="error",
            reason="session_init_failed",
            credential_source=credential_source,
            has_access_key=has_access_key,
            has_secret_key=has_secret_key,
        )
        return None

    _set_auth_state(
        mode="authenticated",
        reason="ok",
        credential_source=credential_source,
        has_access_key=has_access_key,
        has_secret_key=has_secret_key,
    )
    logger.info("Internet Archive authentication initialized.")
    return session
