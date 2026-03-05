"""告警规则引擎测试"""
import pytest
from src.monitor.rule_engine import AlertRule, AlertRuleEngine, MatchType, AlertLevel


def test_keyword_match():
    rule = AlertRule(
        name="error_rule",
        match_type=MatchType.KEYWORD,
        pattern="ERROR",
        level=AlertLevel.CRITICAL
    )
    assert rule.match({"message": "ERROR occurred"}) is True
    assert rule.match({"message": "INFO message"}) is False


def test_regex_match():
    rule = AlertRule(
        name="timeout_rule",
        match_type=MatchType.REGEX,
        pattern=r"timeout.*\d+s",
        level=AlertLevel.WARNING
    )
    assert rule.match({"message": "timeout after 30s"}) is True
    assert rule.match({"message": "timeout"}) is False


def test_level_match():
    rule = AlertRule(
        name="critical_rule",
        match_type=MatchType.LEVEL,
        pattern=["CRITICAL", "FATAL"],
        level=AlertLevel.CRITICAL
    )
    assert rule.match({"level": "CRITICAL"}) is True
    assert rule.match({"level": "INFO"}) is False


def test_field_match():
    rule = AlertRule(
        name="status_rule",
        match_type=MatchType.FIELD,
        pattern="status=failed",
        level=AlertLevel.WARNING
    )
    assert rule.match({"status": "failed"}) is True
    assert rule.match({"status": "success"}) is False


def test_disabled_rule():
    rule = AlertRule(
        name="disabled",
        match_type=MatchType.KEYWORD,
        pattern="ERROR",
        enabled=False
    )
    assert rule.match({"message": "ERROR"}) is False


def test_rule_engine():
    rules = [
        AlertRule("r1", MatchType.KEYWORD, "ERROR", AlertLevel.CRITICAL),
        AlertRule("r2", MatchType.KEYWORD, "WARNING", AlertLevel.WARNING),
    ]
    engine = AlertRuleEngine(rules)

    matched = engine.match_rules({"message": "ERROR occurred"})
    assert len(matched) == 1
    assert matched[0].name == "r1"
