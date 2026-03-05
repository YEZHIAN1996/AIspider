"""MinIO 媒体文件上传模块

将爬虫抓取的媒体文件（图片、视频、文档等）
上传到 MinIO 对象存储。
"""

from __future__ import annotations

import io
import logging
import time
from typing import TYPE_CHECKING

from src.infra.metrics import (
    WRITE_FAIL_TOTAL,
    WRITE_LATENCY,
    WRITE_SUCCESS_TOTAL,
)

if TYPE_CHECKING:
    from miniopy_async import Minio

logger = logging.getLogger(__name__)


class MinioWriter:
    """MinIO 媒体文件上传器

    Args:
        client: miniopy_async Minio 实例
        bucket: 默认存储桶名称
    """

    def __init__(
        self,
        client: Minio,
        bucket: str = "spider-media",
    ) -> None:
        self._client = client
        self._bucket = bucket

    async def ensure_bucket(self) -> None:
        """确保存储桶存在"""
        exists = await self._client.bucket_exists(self._bucket)
        if not exists:
            await self._client.make_bucket(self._bucket)
            logger.info("MinIO bucket 已创建: %s", self._bucket)

    async def upload(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传文件到 MinIO

        Args:
            object_name: 对象键名（如 "images/abc123.jpg"）
            data: 文件二进制内容
            content_type: MIME 类型

        Returns:
            上传后的对象路径
        """
        start = time.monotonic()
        stream = io.BytesIO(data)

        try:
            await self._client.put_object(
                self._bucket,
                object_name,
                stream,
                length=len(data),
                content_type=content_type,
            )
            elapsed = time.monotonic() - start
            WRITE_SUCCESS_TOTAL.labels(target="minio").inc()
            WRITE_LATENCY.labels(target="minio").observe(elapsed)
            return f"{self._bucket}/{object_name}"

        except Exception:
            WRITE_FAIL_TOTAL.labels(target="minio").inc()
            logger.exception(
                "MinIO 上传失败: bucket=%s, object=%s",
                self._bucket, object_name,
            )
            raise
