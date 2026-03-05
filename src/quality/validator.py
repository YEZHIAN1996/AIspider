"""数据校验引擎

根据 QualitySchema 对 item 逐字段校验，
返回校验结果（通过 / 失败 + 错误详情）。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from src.infra.metrics import (
    QUALITY_FAILED,
    QUALITY_PASSED,
    QUALITY_TOTAL,
)
from src.quality.schema import FieldRule, QualitySchema

logger = logging.getLogger(__name__)

# 预编译的 URL / Email 正则
_URL_RE = re.compile(r"^https?://\S+")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class ValidationResult:
    """单条数据的校验结果"""

    is_valid: bool
    errors: list[str]
    cleaned_data: dict | None = None


class DataValidator:
    """数据校验器，根据 QualitySchema 校验 item"""

    # 类型校验映射
    _TYPE_CHECKERS = {
        "str": lambda v: isinstance(v, str),
        "int": lambda v: isinstance(v, int) or (isinstance(v, str) and v.lstrip("-").isdigit()),
        "float": lambda v: _is_float(v),
        "url": lambda v: bool(_URL_RE.match(str(v))),
        "email": lambda v: bool(_EMAIL_RE.match(str(v))),
    }

    def __init__(self, schema: QualitySchema) -> None:
        self.schema = schema
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "fixed": 0,
        }
        # 预编译 regex 规则
        self._compiled_regex: dict[str, re.Pattern] = {}
        for rule in schema.rules:
            if rule.regex:
                self._compiled_regex[rule.field_name] = re.compile(rule.regex)

    def validate(self, item: dict) -> ValidationResult:
        """校验单条数据

        Args:
            item: 待校验的数据字典

        Returns:
            ValidationResult 包含校验结果和错误详情
        """
        self.stats["total"] += 1
        spider = self.schema.spider_name
        QUALITY_TOTAL.labels(spider_name=spider).inc()

        errors: list[str] = []
        for rule in self.schema.rules:
            value = item.get(rule.field_name)
            field_errors = self._check_rule(rule, value)
            for err in field_errors:
                QUALITY_FAILED.labels(
                    spider_name=spider,
                    field=rule.field_name,
                    reason=err,
                ).inc()
            errors.extend(field_errors)

        if errors:
            self.stats["failed"] += 1
            return ValidationResult(is_valid=False, errors=errors)

        self.stats["passed"] += 1
        QUALITY_PASSED.labels(spider_name=spider).inc()
        return ValidationResult(is_valid=True, errors=[], cleaned_data=item)

    def _check_rule(self, rule: FieldRule, value: object) -> list[str]:
        """校验单个字段"""
        errors: list[str] = []
        name = rule.field_name

        # 必填检查
        if rule.required and value is None:
            return [f"{name}: required but missing"]
        if value is None:
            return errors

        # 类型检查
        if rule.field_type:
            checker = self._TYPE_CHECKERS.get(rule.field_type)
            if checker and not checker(value):
                errors.append(f"{name}: expected type {rule.field_type}")

        # 长度检查
        str_val = str(value)
        if rule.min_length is not None and len(str_val) < rule.min_length:
            errors.append(f"{name}: too short (min {rule.min_length})")
        if rule.max_length is not None and len(str_val) > rule.max_length:
            errors.append(f"{name}: too long (max {rule.max_length})")

        # 数值范围检查
        if rule.min_value is not None or rule.max_value is not None:
            try:
                num = float(value)
                if rule.min_value is not None and num < rule.min_value:
                    errors.append(f"{name}: below min value {rule.min_value}")
                if rule.max_value is not None and num > rule.max_value:
                    errors.append(f"{name}: above max value {rule.max_value}")
            except (TypeError, ValueError):
                errors.append(f"{name}: not a number")

        # 枚举检查
        if rule.enum_values and value not in rule.enum_values:
            errors.append(f"{name}: not in allowed values")

        # 正则检查
        if rule.field_name in self._compiled_regex:
            if not self._compiled_regex[rule.field_name].search(str_val):
                errors.append(f"{name}: regex mismatch")

        return errors


def _is_float(value: object) -> bool:
    """判断值是否可转为 float"""
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
