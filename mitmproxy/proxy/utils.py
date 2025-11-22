"""
Utility decorators that help build state machines
"""

import functools

from mitmproxy.proxy import events


def expect(*event_types):
    """
    Only allow the given event type.
    If another event is passed, an AssertionError is raised.
    """

    def decorator(f):
        if __debug__ is True:

            @functools.wraps(f)
            def _check_event_type(self, event: events.Event):
                if isinstance(event, event_types):
                    return f(self, event)
                else:
                    event_types_str = (
                        "|".join(e.__name__ for e in event_types) or "no events"
                    )
                    raise AssertionError(
                        f"Unexpected event type at {f.__qualname__}: "
                        f"Expected {event_types_str}, got {event}."
                    )

            return _check_event_type
        else:  # pragma: no cover
            return f

    return decorator


class ReceiveBuffer:
    """
    A data structure to collect stream contents efficiently in O(n).
    支持内存限制和自动清理机制。
    """

    _chunks: list[bytes]
    _len: int
    _max_size: int | None  # 最大缓存大小（字节）

    def __init__(self, max_size: int | None = None):
        self._chunks = []
        self._len = 0
        self._max_size = max_size

    def __iadd__(self, other: bytes):
        assert isinstance(other, bytes)
        
        # 检查内存限制
        if self._max_size is not None and self._len + len(other) > self._max_size:
            raise MemoryError(f"ReceiveBuffer超出最大限制: {self._max_size}字节")
            
        self._chunks.append(other)
        self._len += len(other)
        return self

    def __len__(self):
        return self._len

    def __bytes__(self):
        return b"".join(self._chunks)

    def __bool__(self):
        return self._len > 0

    def clear(self):
        self._chunks.clear()
        self._len = 0

    def clear_oldest(self, keep_size: int) -> bytes:
        """清理最老的数据，只保留指定大小的数据"""
        if self._len <= keep_size:
            return b""
        
        cleared_data = b""
        remaining_size = keep_size
        new_chunks = []
        
        # 从前往后清理，直到达到保留大小
        for chunk in self._chunks:
            if remaining_size <= 0:
                # 这个chunk需要完全清理
                cleared_data += chunk
            elif len(chunk) <= remaining_size:
                # 这个chunk可以全部保留
                new_chunks.append(chunk)
                remaining_size -= len(chunk)
            else:
                # 这个chunk需要部分保留
                keep_part = chunk[-remaining_size:]
                cleared_part = chunk[:-remaining_size]
                new_chunks.append(keep_part)
                cleared_data += cleared_part
                remaining_size = 0
        
        self._chunks = new_chunks
        self._len = sum(len(chunk) for chunk in new_chunks)
        return cleared_data

    def compact(self) -> None:
        """压缩缓冲区，减少内存碎片"""
        if len(self._chunks) <= 1:
            return
        
        # 将所有chunks合并为一个
        combined = b"".join(self._chunks)
        self._chunks = [combined] if combined else []

    def get_oldest_size(self) -> int:
        """获取最老数据的大小"""
        return len(self._chunks[0]) if self._chunks else 0

    def set_max_size(self, max_size: int | None):
        """动态设置最大缓存大小"""
        self._max_size = max_size

    def get_memory_usage(self) -> int:
        """获取当前内存使用量（估算）"""
        # 计算chunks列表开销 + 实际数据
        overhead = len(self._chunks) * 64  # 每个bytes对象的开销估算
        return self._len + overhead

    def is_full(self) -> bool:
        """检查是否达到内存限制"""
        if self._max_size is None:
            return False
        return self._len >= self._max_size
