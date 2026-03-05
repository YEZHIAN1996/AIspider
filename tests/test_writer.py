"""数据写入测试"""
import pytest
from src.writer.buffer import WriteBuffer


@pytest.mark.asyncio
async def test_write_buffer():
    """测试写入缓冲"""
    buffer = WriteBuffer(max_size=3, flush_interval=5.0)

    # 添加数据
    assert await buffer.add({"id": 1}) is True
    assert await buffer.add({"id": 2}) is True
    assert len(buffer._buffer) == 2


@pytest.mark.asyncio
async def test_buffer_backpressure():
    """测试背压机制"""
    buffer = WriteBuffer(max_size=2, flush_interval=5.0)

    # 填满缓冲区
    for i in range(5):
        await buffer.add({"id": i})

    # 超过2倍阈值应拒绝
    result = await buffer.add({"id": 999})
    assert result is False
