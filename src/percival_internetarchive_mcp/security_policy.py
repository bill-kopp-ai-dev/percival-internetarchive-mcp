from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


ENV_SECURITY_PROFILE = "IA_MCP_SECURITY_PROFILE"
ENV_DEBUG_ERROR_DETAILS = "IA_MCP_DEBUG_ERROR_DETAILS"
ENV_LOG_EXCEPTION_DETAILS = "IA_MCP_LOG_EXCEPTION_DETAILS"
ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS = "IA_MCP_REQUIRE_ALLOWED_DOWNLOAD_DIRS"
ENV_REQUIRE_AUTH = "IA_MCP_REQUIRE_AUTH"
ENV_MARK_UNTRUSTED_CONTENT = "IA_MCP_MARK_UNTRUSTED_CONTENT"
ENV_SANITIZE_UNTRUSTED_TEXT = "IA_MCP_SANITIZE_UNTRUSTED_TEXT"
ENV_MAX_QUERY_LENGTH = "IA_MCP_MAX_QUERY_LENGTH"
ENV_MAX_IDENTIFIER_LENGTH = "IA_MCP_MAX_IDENTIFIER_LENGTH"
ENV_MAX_FILENAME_LENGTH = "IA_MCP_MAX_FILENAME_LENGTH"
ENV_MAX_TEXT_FIELD_CHARS = "IA_MCP_MAX_TEXT_FIELD_CHARS"
ENV_MAX_METADATA_FIELDS = "IA_MCP_MAX_METADATA_FIELDS"
ENV_MAX_METADATA_LIST_ITEMS = "IA_MCP_MAX_METADATA_LIST_ITEMS"
ENV_MAX_FILES_LIST = "IA_MCP_MAX_FILES_LIST"

DEFAULT_SECURITY_PROFILE = "dev"
VALID_SECURITY_PROFILES = {"dev", "staging", "prod"}


@dataclass(frozen=True)
class SecurityPolicyConfig:
    profile: str
    debug_error_details: bool
    log_exception_details: bool
    require_allowed_download_dirs: bool
    require_auth: bool
    mark_untrusted_content: bool
    sanitize_untrusted_text: bool
    max_query_length: int
    max_identifier_length: int
    max_filename_length: int
    max_text_field_chars: int
    max_metadata_fields: int
    max_metadata_list_items: int
    max_files_list: int


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


def _parse_positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _normalize_profile(raw_profile: str) -> str:
    profile = (raw_profile or "").strip().lower()
    if profile in VALID_SECURITY_PROFILES:
        return profile
    return DEFAULT_SECURITY_PROFILE


def _profile_defaults(profile: str) -> dict[str, bool]:
    if profile == "prod":
        return {
            "debug_error_details": False,
            "log_exception_details": False,
            "require_allowed_download_dirs": True,
            "require_auth": True,
            "mark_untrusted_content": True,
            "sanitize_untrusted_text": True,
        }
    if profile == "staging":
        return {
            "debug_error_details": False,
            "log_exception_details": False,
            "require_allowed_download_dirs": True,
            "require_auth": True,
            "mark_untrusted_content": True,
            "sanitize_untrusted_text": True,
        }
    return {
        "debug_error_details": True,
        "log_exception_details": True,
        "require_allowed_download_dirs": False,
        "require_auth": False,
        "mark_untrusted_content": True,
        "sanitize_untrusted_text": True,
    }


def _numeric_defaults(profile: str) -> dict[str, int]:
    if profile == "prod":
        return {
            "max_query_length": 512,
            "max_identifier_length": 200,
            "max_filename_length": 512,
            "max_text_field_chars": 500,
            "max_metadata_fields": 80,
            "max_metadata_list_items": 40,
            "max_files_list": 200,
        }
    if profile == "staging":
        return {
            "max_query_length": 512,
            "max_identifier_length": 200,
            "max_filename_length": 512,
            "max_text_field_chars": 500,
            "max_metadata_fields": 80,
            "max_metadata_list_items": 40,
            "max_files_list": 200,
        }
    return {
        "max_query_length": 1024,
        "max_identifier_length": 300,
        "max_filename_length": 1024,
        "max_text_field_chars": 1000,
        "max_metadata_fields": 120,
        "max_metadata_list_items": 80,
        "max_files_list": 400,
    }


def _load_security_policy_from_env() -> SecurityPolicyConfig:
    profile = _normalize_profile(os.getenv(ENV_SECURITY_PROFILE, DEFAULT_SECURITY_PROFILE))
    bool_defaults = _profile_defaults(profile)
    int_defaults = _numeric_defaults(profile)
    return SecurityPolicyConfig(
        profile=profile,
        debug_error_details=_parse_bool_env(
            ENV_DEBUG_ERROR_DETAILS,
            bool_defaults["debug_error_details"],
        ),
        log_exception_details=_parse_bool_env(
            ENV_LOG_EXCEPTION_DETAILS,
            bool_defaults["log_exception_details"],
        ),
        require_allowed_download_dirs=_parse_bool_env(
            ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS,
            bool_defaults["require_allowed_download_dirs"],
        ),
        require_auth=_parse_bool_env(
            ENV_REQUIRE_AUTH,
            bool_defaults["require_auth"],
        ),
        mark_untrusted_content=_parse_bool_env(
            ENV_MARK_UNTRUSTED_CONTENT,
            bool_defaults["mark_untrusted_content"],
        ),
        sanitize_untrusted_text=_parse_bool_env(
            ENV_SANITIZE_UNTRUSTED_TEXT,
            bool_defaults["sanitize_untrusted_text"],
        ),
        max_query_length=_parse_positive_int_env(
            ENV_MAX_QUERY_LENGTH,
            int_defaults["max_query_length"],
        ),
        max_identifier_length=_parse_positive_int_env(
            ENV_MAX_IDENTIFIER_LENGTH,
            int_defaults["max_identifier_length"],
        ),
        max_filename_length=_parse_positive_int_env(
            ENV_MAX_FILENAME_LENGTH,
            int_defaults["max_filename_length"],
        ),
        max_text_field_chars=_parse_positive_int_env(
            ENV_MAX_TEXT_FIELD_CHARS,
            int_defaults["max_text_field_chars"],
        ),
        max_metadata_fields=_parse_positive_int_env(
            ENV_MAX_METADATA_FIELDS,
            int_defaults["max_metadata_fields"],
        ),
        max_metadata_list_items=_parse_positive_int_env(
            ENV_MAX_METADATA_LIST_ITEMS,
            int_defaults["max_metadata_list_items"],
        ),
        max_files_list=_parse_positive_int_env(
            ENV_MAX_FILES_LIST,
            int_defaults["max_files_list"],
        ),
    )


_security_policy: SecurityPolicyConfig = _load_security_policy_from_env()


def reload_security_policy_config() -> dict[str, Any]:
    global _security_policy
    _security_policy = _load_security_policy_from_env()
    return get_security_policy_summary()


def get_security_policy_config() -> SecurityPolicyConfig:
    return _security_policy


def get_security_policy_summary() -> dict[str, Any]:
    policy = _security_policy
    return {
        "profile": policy.profile,
        "debug_error_details": policy.debug_error_details,
        "log_exception_details": policy.log_exception_details,
        "require_allowed_download_dirs": policy.require_allowed_download_dirs,
        "require_auth": policy.require_auth,
        "mark_untrusted_content": policy.mark_untrusted_content,
        "sanitize_untrusted_text": policy.sanitize_untrusted_text,
        "limits": {
            "max_query_length": policy.max_query_length,
            "max_identifier_length": policy.max_identifier_length,
            "max_filename_length": policy.max_filename_length,
            "max_text_field_chars": policy.max_text_field_chars,
            "max_metadata_fields": policy.max_metadata_fields,
            "max_metadata_list_items": policy.max_metadata_list_items,
            "max_files_list": policy.max_files_list,
        },
        "env": {
            "profile": ENV_SECURITY_PROFILE,
            "debug_error_details": ENV_DEBUG_ERROR_DETAILS,
            "log_exception_details": ENV_LOG_EXCEPTION_DETAILS,
            "require_allowed_download_dirs": ENV_REQUIRE_ALLOWED_DOWNLOAD_DIRS,
            "require_auth": ENV_REQUIRE_AUTH,
            "mark_untrusted_content": ENV_MARK_UNTRUSTED_CONTENT,
            "sanitize_untrusted_text": ENV_SANITIZE_UNTRUSTED_TEXT,
            "max_query_length": ENV_MAX_QUERY_LENGTH,
            "max_identifier_length": ENV_MAX_IDENTIFIER_LENGTH,
            "max_filename_length": ENV_MAX_FILENAME_LENGTH,
            "max_text_field_chars": ENV_MAX_TEXT_FIELD_CHARS,
            "max_metadata_fields": ENV_MAX_METADATA_FIELDS,
            "max_metadata_list_items": ENV_MAX_METADATA_LIST_ITEMS,
            "max_files_list": ENV_MAX_FILES_LIST,
        },
    }
