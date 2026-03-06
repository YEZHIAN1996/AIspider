"""通用工具函数"""

import json
from typing import Any


def safe_json_decode(raw: bytes | str | None, default: Any = None) -> Any:
    """安全解码 JSON，失败时返回默认值"""
    if raw is None:
        return default
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default
