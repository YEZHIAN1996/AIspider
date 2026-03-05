"""数据清洗模块

提供通用清洗策略：
- 去除首尾空白
- HTML 标签清理
- Unicode 规范化
- 默认值填充
- 类型强制转换
"""

from __future__ import annotations

import html
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# 预编译 HTML 标签正则
_HTML_TAG_RE = re.compile(r"<[^>]+>")
# 连续空白压缩
_MULTI_SPACE_RE = re.compile(r"\s+")


class DataCleaner:
    """通用数据清洗器

    Args:
        defaults: 字段默认值映射，缺失时自动填充
        type_coerce: 字段类型强制转换映射，如 {"price": float}
    """

    def __init__(
        self,
        defaults: dict[str, object] | None = None,
        type_coerce: dict[str, type] | None = None,
    ) -> None:
        self._defaults = defaults or {}
        self._type_coerce = type_coerce or {}

    def clean(self, item: dict) -> dict:
        """对 item 执行全部清洗步骤"""
        cleaned = {}
        for key, value in item.items():
            value = self._strip_whitespace(value)
            value = self._strip_html(value)
            value = self._normalize_unicode(value)
            cleaned[key] = value

        # 默认值填充
        for field, default in self._defaults.items():
            if field not in cleaned or cleaned[field] is None:
                cleaned[field] = default

        # 类型强制转换
        for field, target_type in self._type_coerce.items():
            if field in cleaned and cleaned[field] is not None:
                cleaned[field] = self._coerce(field, cleaned[field], target_type)

        return cleaned

    @staticmethod
    def _strip_whitespace(value: object) -> object:
        """去除首尾空白，压缩连续空白"""
        if not isinstance(value, str):
            return value
        value = value.strip()
        return _MULTI_SPACE_RE.sub(" ", value)

    @staticmethod
    def _strip_html(value: object) -> object:
        """移除 HTML 标签并解码实体"""
        if not isinstance(value, str):
            return value
        value = _HTML_TAG_RE.sub("", value)
        return html.unescape(value)

    @staticmethod
    def _normalize_unicode(value: object) -> object:
        """Unicode NFC 规范化"""
        if not isinstance(value, str):
            return value
        return unicodedata.normalize("NFC", value)

    @staticmethod
    def _coerce(field: str, value: object, target_type: type) -> object:
        """类型强制转换，失败时返回原值"""
        try:
            return target_type(value)
        except (TypeError, ValueError):
            logger.warning(
                "类型转换失败: field=%s, value=%r, target=%s",
                field, value, target_type.__name__,
            )
            return value
