"""数据校验测试"""
import pytest
from src.quality.validator import DataValidator
from src.quality.schema import QualitySchema, FieldRule


def test_validator_required_field():
    schema = QualitySchema(
        spider_name="test",
        rules=[FieldRule(field_name="title", required=True)]
    )
    validator = DataValidator(schema)

    result = validator.validate({"title": "test"})
    assert result.is_valid is True

    result = validator.validate({})
    assert result.is_valid is False
    assert "required" in result.errors[0]


def test_validator_type_check():
    schema = QualitySchema(
        spider_name="test",
        rules=[FieldRule(field_name="price", field_type="int")]
    )
    validator = DataValidator(schema)

    result = validator.validate({"price": 100})
    assert result.is_valid is True

    result = validator.validate({"price": "abc"})
    assert result.is_valid is False


def test_validator_length_check():
    schema = QualitySchema(
        spider_name="test",
        rules=[FieldRule(field_name="title", min_length=5, max_length=20)]
    )
    validator = DataValidator(schema)

    result = validator.validate({"title": "hello"})
    assert result.is_valid is True

    result = validator.validate({"title": "hi"})
    assert result.is_valid is False
    assert "too short" in result.errors[0]
