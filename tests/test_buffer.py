"""写入缓冲测试"""
import pytest
import asyncio
from src.writer.buffer import WriteBuffer


@pytest.mark.asyncio
async def test_buffer_flush_on_size():
    flushed = []
    async def flush_cb(batch):
        flushed.extend(batch)

    buffer = WriteBuffer("test", flush_cb, max_size=3, flush_interval=10.0)
    await buffer.add({"id": 1})
    await buffer.add({"id": 2})
    await buffer.add({"id": 3})

    await asyncio.sleep(0.1)
    assert len(flushed) == 3


@pytest.mark.asyncio
async def test_buffer_backpressure():
    async def flush_cb(batch):
        await asyncio.sleep(1)

    buffer = WriteBuffer("test", flush_cb, max_size=2, flush_interval=10.0)
    for i in range(4):
        await buffer.add({"id": i})

    result = await buffer.add({"id": 999})
    assert result is False


@pytest.mark.asyncio
async def test_buffer_flush_on_timeout():
    flushed = []
    async def flush_cb(batch):
        flushed.extend(batch)

    buffer = WriteBuffer("test", flush_cb, max_size=100, flush_interval=0.5)
    await buffer.add({"id": 1})

    await asyncio.sleep(0.6)
    assert len(flushed) == 1
