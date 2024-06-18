import struct

from .domain_names import unpack_from

_LENGTH_LABEL = struct.Struct("!H")
_MESSAGE_HEADERS = struct.Struct("!HHHHHH")


def starts_like_dns_record(data: bytes) -> bool:
    try:
        offset = 0
        (
            id,
            flags,
            len_questions,
            len_answers,
            len_authorities,
            len_additionals,
        ) = _MESSAGE_HEADERS.unpack_from(data, offset)
        offset += _MESSAGE_HEADERS.size
        name, offset = unpack_from(data[offset:], offset)
    except:
        return False
    else:
        return True


def starts_like_dns_over_tcp_record(data: bytes) -> bool:
    offset = 0
    try:
        (length,) = _LENGTH_LABEL.unpack_from(data, offset)
        offset += _LENGTH_LABEL.size
    except:
        return False

    if length >= len(data[offset:]) and starts_like_dns_record(data[offset:]):
        return True
    else:
        return False
