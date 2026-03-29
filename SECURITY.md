# Security Baseline

This document defines baseline security posture for the MCP wrapper layer.

## Scope

- Applies only to wrapper code in `src/percival_internetarchive_mcp/`.
- Does not modify vendored upstream `internetarchive/`.

## Security Profiles

Security behavior is controlled by `IA_MCP_SECURITY_PROFILE`:

- `dev` (default): permissive for local development.
- `staging`: production-like guardrails for pre-prod validation.
- `prod`: strictest defaults.

## Environment Controls

- `IA_MCP_SECURITY_PROFILE`
- `IA_MCP_DEBUG_ERROR_DETAILS`
- `IA_MCP_LOG_EXCEPTION_DETAILS`
- `IA_MCP_REQUIRE_ALLOWED_DOWNLOAD_DIRS`
- `IA_MCP_REQUIRE_AUTH`
- `IA_MCP_MARK_UNTRUSTED_CONTENT`
- `IA_MCP_SANITIZE_UNTRUSTED_TEXT`
- `IA_MCP_MAX_QUERY_LENGTH`
- `IA_MCP_MAX_IDENTIFIER_LENGTH`
- `IA_MCP_MAX_FILENAME_LENGTH`
- `IA_MCP_MAX_TEXT_FIELD_CHARS`
- `IA_MCP_MAX_METADATA_FIELDS`
- `IA_MCP_MAX_METADATA_LIST_ITEMS`
- `IA_MCP_MAX_FILES_LIST`
- `IA_MCP_ALLOWED_DOWNLOAD_DIRS`
- `IA_MCP_FORBIDDEN_DOWNLOAD_DIRS`
- `IA_MCP_MAX_DOWNLOAD_BYTES`
- `IA_MCP_DOWNLOAD_TIMEOUT_SECONDS`

## Default Policy Matrix

- `dev`:
  - `debug_error_details=true`
  - `log_exception_details=true`
  - `require_allowed_download_dirs=false`
  - `require_auth=false`
  - `mark_untrusted_content=true`
  - `sanitize_untrusted_text=true`
- `staging`:
  - `debug_error_details=false`
  - `log_exception_details=false`
  - `require_allowed_download_dirs=true`
  - `require_auth=true`
  - `mark_untrusted_content=true`
  - `sanitize_untrusted_text=true`
- `prod`:
  - `debug_error_details=false`
  - `log_exception_details=false`
  - `require_allowed_download_dirs=true`
  - `require_auth=true`
  - `mark_untrusted_content=true`
  - `sanitize_untrusted_text=true`

## Download Fail-Closed Rule

When `require_allowed_download_dirs=true`, download requests are denied if `IA_MCP_ALLOWED_DOWNLOAD_DIRS` is empty or missing.

## Error Detail Hygiene

When `debug_error_details=false`, internal exception text is removed from MCP error payloads before responses are returned to clients.

When `log_exception_details=false`, stack-style exception logging is suppressed in favor of minimal operational log messages.

## Prompt-Injection Mitigation

- Tool responses sourced from Internet Archive are tagged as untrusted in `meta`.
- Text fields from external content are normalized/sanitized.
- Agents should treat all tool-returned text as data, never as executable instruction.

## Payload Minimization

- Query, identifier and filename length limits are enforced.
- Metadata responses are bounded by field count and list sizes.
- Oversized text values are truncated.
- File lists from metadata are capped and return truncation signals.

## Runtime Observability

- `get_server_status()` exposes active `security_policy`.
- `get_server_status()` exposes auth compliance (`required_by_policy`, `compliant`, `reason`).
- `get_server_status()` exposes evaluated `security_posture` checks.
- `reload_runtime_config()` reloads security policy plus governance/rollout settings.
- `reload_runtime_config()` can fail with `SECURITY_POSTURE_NON_COMPLIANT` when rollout `phase2` is active and posture checks fail.

## Phase2 Security Gate

In rollout `phase2`, runtime posture must remain compliant. The gate validates at least:

- profile is `staging` or `prod`
- auth policy is required and currently compliant
- allowlist policy is required and configured
- strict-profile redaction/log rules are active
- legacy shims/resource compatibility flags remain disabled
