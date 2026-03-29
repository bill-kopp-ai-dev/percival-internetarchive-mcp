# Migration Guide: Legacy -> Nanobot-first MCP

This document covers migration from the legacy launcher/import style to the standardized MCP wrapper (`uv + pyproject.toml + FastMCP`).

## Goals

- Keep vendored upstream (`internetarchive/`) untouched.
- Stabilize a strict Nanobot-first tool contract.
- Remove implicit download folder behavior.
- Provide gradual compatibility via rollout phases.

## Runtime Migration

Preferred runtime:

```bash
uv run --directory /absolute/path/to/percival-internetarchive-mcp percival-internetarchive-mcp
```

Legacy compatibility (still supported while rollout allows):

```bash
python /absolute/path/to/percival-internetarchive-mcp/server.py
```

## MCP Contract Migration

All tools now return a JSON envelope:

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

For Internet Archive sourced text (`search_archive`, `get_archive_metadata`), `meta` now includes untrusted-content markers. Clients must treat returned text as data only.

Failure format:

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

## Download Flow Migration

Old pattern:

- implicit server-side destination folder.
- post-download file moves.

New pattern:

- Nanobot passes destination explicitly through `destination_dir`.
- file is written directly to final target path.
- optional `destination_filename` supports rename on write.

Compatibility transition:

- empty `destination_dir` can be accepted only when rollout allows it and a fallback dir is configured (`IA_MCP_DEFAULT_DOWNLOAD_DIR`).

## Tool Surface

Current MCP tools:

- `search_archive(query, limit=5)`
- `get_archive_metadata(identifier)`
- `download_archive_file(identifier, filename, destination_dir, destination_filename="", overwrite=false)`
- `get_server_status()`
- `reload_runtime_config()`
- `get_security_posture()`

Compatibility resource (phase-dependent):

- `archive://{identifier}/metadata`

## Legacy Shims

Root-level compatibility modules remain available (`server.py`, `tools.py`, `auth.py`, `ia_bootstrap.py`).

`tools.py` execute aliases can be disabled by rollout policy in strict phase.

## Recommended Nanobot Integration

- Always pass explicit `destination_dir`.
- Call `get_archive_metadata` before download to validate exact filename.
- Use `get_server_status` for telemetry/policy checks.
- Use `get_security_posture` as explicit rollout preflight before strict phase promotion.
- Use `reload_runtime_config` after environment flag changes.
- Set `IA_MCP_SECURITY_PROFILE=prod` in production and configure `IA_MCP_ALLOWED_DOWNLOAD_DIRS`.
- Handle `metadata`/`files` truncation flags (`data.limits`, `data.files_truncated`) when processing large items.
- For strict profiles, provide IA credentials; otherwise `reload_runtime_config()` can return `AUTH_REQUIRED`.
- In `phase2`, non-compliant runtime security posture now blocks with `SECURITY_POSTURE_NON_COMPLIANT`.
