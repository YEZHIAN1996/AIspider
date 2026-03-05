"""MinIO 媒体文件 Pipeline

处理 item 中的媒体文件字段，
上传到 MinIO 并替换为对象路径。
"""

from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)


class MinIOMediaPipeline:
    """Scrapy Pipeline: 媒体文件上传到 MinIO"""

    def open_spider(self, spider):
        self._writer = None
        self._media_fields = getattr(spider, "media_fields", [])
        self._warned_not_ready = False

    async def process_item(self, item, spider):
        if not self._media_fields:
            return item

        # 延迟初始化 writer
        if self._writer is None:
            from src.writer.minio_writer import MinioWriter
            conn = getattr(spider, "_conn_manager", None)
            if conn and conn.is_started:
                self._writer = MinioWriter(conn.minio)
                await self._writer.ensure_bucket()
            elif not self._warned_not_ready:
                logger.error(
                    "MinIO Pipeline 连接未就绪，暂不可上传媒体: spider=%s",
                    spider.name,
                )
                self._warned_not_ready = True

        if self._writer is None:
            return item

        data = dict(item)
        for field in self._media_fields:
            content = data.get(field)
            if not isinstance(content, bytes):
                continue
            ext = data.get(f"{field}_ext", "bin")
            name = hashlib.md5(content).hexdigest()
            obj_name = f"{spider.name}/{name}.{ext}"
            path = await self._writer.upload(obj_name, content)
            data[field] = path

        return data
