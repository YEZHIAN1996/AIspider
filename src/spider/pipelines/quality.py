"""数据质量校验 Pipeline

在 Scrapy Pipeline 中集成数据质量校验，
校验失败的 item 根据策略隔离或丢弃。
"""

from __future__ import annotations

import logging

from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class DataQualityPipeline:
    """Scrapy Pipeline: 数据质量校验

    从 spider.custom_settings 或全局配置中加载校验规则，
    校验失败时根据 on_fail 策略处理。
    """

    def open_spider(self, spider):
        from src.quality.schema import QualitySchema
        from src.quality.validator import DataValidator
        from src.quality.cleaner import DataCleaner

        # 从 spider 的 custom_settings 加载校验规则
        schema_config = getattr(spider, "quality_schema", None)
        if schema_config and isinstance(schema_config, QualitySchema):
            self._validator = DataValidator(schema_config)
        else:
            self._validator = None

        # 清洗器
        cleaner_config = getattr(spider, "cleaner_config", {})
        self._cleaner = DataCleaner(**cleaner_config)
        self._spider_name = spider.name

    def process_item(self, item, spider):
        """清洗 + 校验"""
        data = dict(item)

        # 1. 数据清洗
        data = self._cleaner.clean(data)

        # 2. 数据校验
        if self._validator is None:
            return data

        result = self._validator.validate(data)
        if result.is_valid:
            return result.cleaned_data

        on_fail = self._validator.schema.on_fail
        if on_fail == "drop":
            raise DropItem(
                f"校验失败({self._spider_name}): {result.errors}"
            )

        # quarantine / fix 策略：标记后继续传递，由后续 pipeline 处理
        data["_quality_errors"] = result.errors
        data["_quality_action"] = on_fail
        return data
