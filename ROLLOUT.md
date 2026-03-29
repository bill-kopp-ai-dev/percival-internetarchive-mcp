# Controlled Rollout Playbook

This playbook defines how to move safely from compatibility mode to strict Nanobot-first operation.

## Rollout Phases

## `phase0` (compatibility-first)

- compatibility resource enabled
- legacy shim aliases enabled
- empty `destination_dir` can fallback when `IA_MCP_DEFAULT_DOWNLOAD_DIR` is set

Use this phase only for short migration windows.

## `phase1` (default, balanced)

- compatibility resource enabled
- legacy shim aliases enabled
- explicit destination expected (empty destination disabled by default)

Recommended for active migration.

## `phase2` (strict)

- compatibility resource disabled
- legacy shim aliases disabled
- explicit destination required

Use when all clients are migrated to Nanobot-first MCP contract.

## Environment Flags

- `IA_MCP_ROLLOUT_PHASE`
- `IA_MCP_COMPAT_RESOURCE_ENABLED`
- `IA_MCP_LEGACY_SHIMS_ENABLED`
- `IA_MCP_ALLOW_EMPTY_DESTINATION`
- `IA_MCP_DEFAULT_DOWNLOAD_DIR`

Override flags allow canary behavior without changing global phase.

## Runtime Procedure

1. Set env vars for target phase.
2. Start server (or restart it for registration-sensitive changes such as resource exposure).
3. Call `reload_runtime_config()` to refresh runtime-governance and rollout settings.
4. Call `get_server_status()` and confirm:
   - `data.security_policy`
   - `data.security_posture` (`compliant=true` before production promotion)
   - `data.rollout`
   - `data.download_governance`
   - `data.auth.required_by_policy` and `data.auth.compliant`
   - telemetry remains healthy (`total_errors`, per-tool errors)
   - truncation/error-rate behavior remains stable for metadata-heavy items
5. Optionally call `get_security_posture()` directly as a preflight gate.

## Suggested Rollout Sequence

1. Deploy `phase1` in staging and validate Nanobot explicit destination flow.
2. Deploy `phase1` in production with telemetry watch.
3. Run limited canary with `phase2` for selected agents and require `security_posture.compliant=true`.
4. Promote `phase2` after zero regression window.

## Rollback Strategy

If regressions occur:

1. Set `IA_MCP_ROLLOUT_PHASE=phase1` (or `phase0` if emergency compatibility is needed).
2. Call `reload_runtime_config()` and verify with `get_server_status()`.
3. If issue is resource registration visibility, restart server process.

Keep rollback fast by preparing env manifests for all three phases in advance.
