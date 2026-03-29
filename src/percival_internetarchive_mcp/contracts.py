from __future__ import annotations

from typing import Any


def success_response(tool: str, data: Any, **meta: Any) -> dict[str, Any]:
    response: dict[str, Any] = {
        "ok": True,
        "data": data,
        "error": None,
        "meta": {"tool": tool},
    }
    if meta:
        response["meta"].update(meta)
    return response


def error_response(
    tool: str,
    code: str,
    message: str,
    *,
    details: Any | None = None,
    **meta: Any,
) -> dict[str, Any]:
    error_payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error_payload["details"] = details

    response: dict[str, Any] = {
        "ok": False,
        "data": None,
        "error": error_payload,
        "meta": {"tool": tool},
    }
    if meta:
        response["meta"].update(meta)
    return response
