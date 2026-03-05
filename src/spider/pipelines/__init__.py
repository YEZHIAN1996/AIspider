"""Scrapy Pipelines 公共接口"""

from src.spider.pipelines.quality import DataQualityPipeline
from src.spider.pipelines.media import MinIOMediaPipeline
from src.spider.pipelines.postgres import PostgresWriterPipeline
from src.spider.pipelines.kafka import KafkaStreamPipeline

__all__ = [
    "DataQualityPipeline",
    "MinIOMediaPipeline",
    "PostgresWriterPipeline",
    "KafkaStreamPipeline",
]
