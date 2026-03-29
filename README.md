# percival-internetarchive-mcp

Security-focused MCP wrapper for Internet Archive, standardized with `uv + pyproject.toml + FastMCP`, and optimized for Nanobot workflows.

## Project Origin

This project is built on top of the original Internet Archive Python project:

- Original upstream: https://github.com/jjjake/internetarchive

The upstream code is vendored under:

- `percival-internetarchive-mcp/internetarchive/`

Wrapper-specific MCP logic lives under:

- `percival-internetarchive-mcp/src/percival_internetarchive_mcp/`

This wrapper intentionally keeps upstream behavior isolated while adding MCP contracts, security guardrails, and operational controls for agent usage.

## What This Project Adds

### Nanobot-First Optimization

- Stable JSON envelope contract for all tools: `ok`, `data`, `error`, `meta`
- Direct-to-destination downloads (no intermediate server-local download folder)
- Explicit truncation metadata for large payloads (`limits`, `files_truncated`, `text_truncations`)
- Runtime observability tools for agent decision loops:
  - `get_server_status()`
  - `reload_runtime_config()`
  - `get_security_posture()`

### Security Hardening

- Profile-driven security policy (`dev`, `staging`, `prod`)
- Fail-closed destination governance with allowlist enforcement
- Auth requirement gates for strict profiles
- Error detail redaction and exception logging hygiene
- Prompt-injection mitigation markers for untrusted external content
- Rollout-phase enforcement with strict `phase2` security posture checks

### MCP Standardization

- `FastMCP` server implementation
- `pyproject.toml` packaging and script entrypoint
- `uv` workflow and lockfile
- Compatibility shims controlled by rollout flags

## Tool Surface

- `search_archive(query, limit=5)`
- `get_archive_metadata(identifier)`
- `download_archive_file(identifier, filename, destination_dir, destination_filename="", overwrite=false)`
- `get_server_status()`
- `reload_runtime_config()`
- `get_security_posture()`

Compatibility resource (phase-dependent):

- `archive://{identifier}/metadata`

## Shared Virtual Environment Model

This server is designed to run from the shared workspace environment:

- Shared environment: `percival.OS_Dev/.venv`
- No server-local `.venv` required

Install into the shared environment (editable mode):

```bash
UV_CACHE_DIR=/tmp/uv-cache uv pip install \
  --python /home/bill-kopp/Documents/percival.OS/percival.OS_Dev/.venv/bin/python \
  -e /home/bill-kopp/Documents/percival.OS/percival.OS_Dev/mcp_servers/percival-internetarchive-mcp
```

Run the server:

```bash
/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/.venv/bin/percival-internetarchive-mcp
```

## Nanobot Integration Example

```json
{
  "mcpServers": {
    "percival-internetarchive": {
      "command": "/home/bill-kopp/Documents/percival.OS/percival.OS_Dev/.venv/bin/percival-internetarchive-mcp",
      "env": {
        "MCP_LOG_LEVEL": "INFO",
        "IA_MCP_SECURITY_PROFILE": "prod",
        "IA_MCP_ALLOWED_DOWNLOAD_DIRS": "/home/bill-kopp/Documents/percival.OS/downloads",
        "IA_MCP_ROLLOUT_PHASE": "phase1"
      }
    }
  }
}
```

## Security Controls

### Security Profiles

- `IA_MCP_SECURITY_PROFILE=dev|staging|prod`
- `staging` and `prod` default to strict behavior:
  - `require_auth=true`
  - `require_allowed_download_dirs=true`
  - `debug_error_details=false`
  - `log_exception_details=false`

### Download Governance

- `IA_MCP_ALLOWED_DOWNLOAD_DIRS`
- `IA_MCP_FORBIDDEN_DOWNLOAD_DIRS`
- `IA_MCP_MAX_DOWNLOAD_BYTES`
- `IA_MCP_DOWNLOAD_TIMEOUT_SECONDS`

### Prompt-Injection and Output Safety

- External content is marked as untrusted in tool metadata
- Untrusted text is sanitized/normalized before returning
- Metadata/file payloads are bounded and truncation is explicit

### Runtime Compliance Gates

- `reload_runtime_config()` may return:
  - `AUTH_REQUIRED`
  - `SECURITY_POSTURE_NON_COMPLIANT`
- `get_security_posture()` exposes check-level compliance for rollout preflight

## Rollout Model

- `phase0`: compatibility-first
- `phase1`: default balanced mode
- `phase2`: strict mode (legacy compatibility disabled)

Environment flags:

- `IA_MCP_ROLLOUT_PHASE`
- `IA_MCP_COMPAT_RESOURCE_ENABLED`
- `IA_MCP_LEGACY_SHIMS_ENABLED`
- `IA_MCP_ALLOW_EMPTY_DESTINATION`
- `IA_MCP_DEFAULT_DOWNLOAD_DIR`

## Response Contract

Success:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "tool": "tool_name",
    "request_id": "...",
    "duration_ms": 12.34
  }
}
```

Error:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  },
  "meta": {
    "tool": "tool_name"
  }
}
```

## Additional Documentation

- [SECURITY.md](SECURITY.md)
- [ROLLOUT.md](ROLLOUT.md)
- [MIGRATION.md](MIGRATION.md)
