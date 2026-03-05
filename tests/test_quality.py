"""数据质量测试"""
import pytest
from src.quality.validator import DataValidator
from src.quality.schema import QualitySchema, FieldRule


def test_validator_pass():
    """测试数据校验通过"""
    schema = QualitySchema(
        spider_name="test",
        rules=[
            FieldRule(field_name="title", required=True, min_length=1),
            FieldRule(field_name="price", required=True, field_type="float", min_value=0),
        ]
    )
    validator = DataValidator(schema)

    result = validator.validate({"title": "Test Product", "price": 99.9})
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validator_fail():
    """测试数据校验失败"""
    schema = QualitySchema(
        spider_name="test",
        rules=[
            FieldRule(field_name="title", required=True),
        ]
    )
    validator = DataValidator(schema)

    result = validator.validate({"price": 100})
    assert result.is_valid is False
    assert len(result.errors) > 0
