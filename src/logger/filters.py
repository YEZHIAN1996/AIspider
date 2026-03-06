"""日志过滤器 - 过滤敏感信息"""

import re
from typing import Any


# 敏感字段模式
SENSITIVE_PATTERNS = {
    "password", "passwd", "pwd", "secret", "token", "key",
    "authorization", "auth", "credential", "api_key", "access_key"
}


def mask_sensitive_value(value: Any) -> str:
    """遮蔽敏感值"""
    if value is None:
        return "None"
    s = str(value)
    if len(s) <= 4:
        return "***"
    return f"{s[:2]}***{s[-2:]}"


def filter_sensitive_data(data: dict) -> dict:
    """过滤字典中的敏感信息"""
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SENSITIVE_PATTERNS):
            filtered[key] = mask_sensitive_value(value)
        elif isinstance(value, dict):
            filtered[key] = filter_sensitive_data(value)
        else:
            filtered[key] = value
    return filtered
