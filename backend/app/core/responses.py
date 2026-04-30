from __future__ import annotations

from typing import Any


def success(data: Any = None, message: str = "success", code: int = 0) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def error(message: str, code: int = 1, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}
