"""数据质量校验规则定义

声明式配置校验规则，支持：
- 字段必填 / 类型 / 长度 / 范围 / 枚举 / 正则
- 自定义校验函数
- 校验失败策略（隔离 / 丢弃 / 自动修复）
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FieldRule(BaseModel):
    """单个字段的校验规则"""

    field_name: str
    required: bool = False
    field_type: str | None = None  # str, int, float, url, email
    regex: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    enum_values: list[Any] | None = None
    custom_func: str | None = None  # 自定义校验函数名


class QualitySchema(BaseModel):
    """一个 Spider 的数据质量规则集"""

    spider_name: str
    rules: list[FieldRule]
    on_fail: str = "quarantine"  # quarantine | drop | fix
