import struct
from typing import Optional

_LABEL_SIZE = struct.Struct("!B")
_POINTER_OFFSET = struct.Struct("!H")
_POINTER_INDICATOR = 0b11000000


Cache = dict[int, Optional[tuple[str, int]]]


def cache() -> Cache:
    return dict()


def _unpack_label_into(labels: list[str], buffer: bytes, offset: int) -> int:
    (size,) = _LABEL_SIZE.unpack_from(buffer, offset)
    if size >= 64:
        raise struct.error(f"unpack encountered a label of length {size}")
    elif size == 0:
        return _LABEL_SIZE.size
    else:
        offset += _LABEL_SIZE.size
        end_label = offset + size
        if len(buffer) < end_label:
            raise struct.error(f"unpack requires a label buffer of {size} bytes")
        try:
            labels.append(buffer[offset:end_label].decode("idna"))
        except UnicodeDecodeError:
            raise struct.error(
                f"unpack encountered a illegal characters at offset {offset}"
            )
        return _LABEL_SIZE.size + size


def unpack_from_with_compression(
    buffer: bytes, offset: int, cache: Cache
) -> tuple[str, int]:
    if offset in cache:
        result = cache[offset]
        if result is None:
            raise struct.error(f"unpack encountered domain name loop")
    else:
        cache[offset] = None  # this will indicate that the offset is being unpacked
        start_offset = offset
        labels = []
        while True:
            (size,) = _LABEL_SIZE.unpack_from(buffer, offset)
            if size & _POINTER_INDICATOR == _POINTER_INDICATOR:
                (pointer,) = _POINTER_OFFSET.unpack_from(buffer, offset)
                offset += _POINTER_OFFSET.size
                label, _ = unpack_from_with_compression(
                    buffer, pointer & ~(_POINTER_INDICATOR << 8), cache
                )
                labels.append(label)
                break
            else:
                offset += _unpack_label_into(labels, buffer, offset)
                if size == 0:
                    break
        result = ".".join(labels), (offset - start_offset)
        cache[start_offset] = result
    return result


def unpack_from(buffer: bytes, offset: int) -> tuple[str, int]:
    """Converts RDATA into a domain name without pointer compression from a given offset and also returns the binary size."""
    labels: list[str] = []
    while True:
        (size,) = _LABEL_SIZE.unpack_from(buffer, offset)
        if size & _POINTER_INDICATOR == _POINTER_INDICATOR:
            raise struct.error(
                f"unpack encountered a pointer which is not supported in RDATA"
            )
        else:
            offset += _unpack_label_into(labels, buffer, offset)
            if size == 0:
                break
    return ".".join(labels), offset


def unpack(buffer: bytes) -> str:
    """Converts RDATA into a domain name without pointer compression."""
    name, length = unpack_from(buffer, 0)
    if length != len(buffer):
        raise struct.error(f"unpack requires a buffer of {length} bytes")
    return name


def pack(name: str) -> bytes:
    """Converts a domain name into RDATA without pointer compression."""
    buffer = bytearray()
    if len(name) > 0:
        for part in name.split("."):
            label = part.encode("idna")
            size = len(label)
            if size == 0:
                raise ValueError(f"domain name '{name}' contains empty labels")
            if size >= 64:  # pragma: no cover
                # encoding with 'idna' will already have raised an exception earlier
                raise ValueError(
                    f"encoded label '{part}' of domain name '{name}' is too long ({size} bytes)"
                )
            buffer.extend(_LABEL_SIZE.pack(size))
            buffer.extend(label)
    buffer.extend(_LABEL_SIZE.pack(0))
    return bytes(buffer)
