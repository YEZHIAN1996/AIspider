"""告警规则引擎

支持从 YAML 配置文件加载告警规则，支持多种匹配条件和告警级别。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MatchType(str, Enum):
    KEYWORD = "keyword"
    REGEX = "regex"
    LEVEL = "level"
    FIELD = "field"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    match_type: MatchType
    pattern: str | list[str]
    level: AlertLevel = AlertLevel.WARNING
    enabled: bool = True
    _compiled_regex: re.Pattern | None = None

    def __post_init__(self):
        if self.match_type == MatchType.REGEX:
            self._compiled_regex = re.compile(self.pattern)

    def match(self, log_entry: dict) -> bool:
        """检查日志是否匹配规则"""
        if not self.enabled:
            return False

        if self.match_type == MatchType.KEYWORD:
            message = log_entry.get("message", "")
            patterns = [self.pattern] if isinstance(self.pattern, str) else self.pattern
            return any(p in message for p in patterns)

        elif self.match_type == MatchType.REGEX:
            message = log_entry.get("message", "")
            return bool(self._compiled_regex.search(message))

        elif self.match_type == MatchType.LEVEL:
            level = log_entry.get("level", "")
            patterns = [self.pattern] if isinstance(self.pattern, str) else self.pattern
            return level in patterns

        elif self.match_type == MatchType.FIELD:
            field, value = self.pattern.split("=", 1)
            return str(log_entry.get(field, "")) == value

        return False


class AlertRuleEngine:
    """告警规则引擎"""

    def __init__(self, rules: list[AlertRule]):
        self.rules = rules

    def match_rules(self, log_entry: dict) -> list[AlertRule]:
        """返回所有匹配的规则"""
        return [rule for rule in self.rules if rule.match(log_entry)]

    @classmethod
    def from_yaml(cls, yaml_path: str) -> AlertRuleEngine:
        """从 YAML 文件加载规则"""
        import yaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        rules = []
        for rule_data in data.get("rules", []):
            rules.append(AlertRule(
                name=rule_data["name"],
                match_type=MatchType(rule_data["match_type"]),
                pattern=rule_data["pattern"],
                level=AlertLevel(rule_data.get("level", "warning")),
                enabled=rule_data.get("enabled", True),
            ))
        return cls(rules)
