"""
tnetstring:  data serialization using typed netstrings
======================================================

This is a custom Python 3 implementation of tnetstrings.
Compared to other implementations, the main difference
is that this implementation supports a custom unicode datatype.

An ordinary tnetstring is a blob of data prefixed with its length and postfixed
with its type. Here are some examples:

    >>> tnetstring.dumps("hello world")
    11:hello world,
    >>> tnetstring.dumps(12345)
    5:12345#
    >>> tnetstring.dumps([12345, True, 0])
    19:5:12345#4:true!1:0#]

This module gives you the following functions:

    :dump:    dump an object as a tnetstring to a file
    :dumps:   dump an object as a tnetstring to a string
    :load:    load a tnetstring-encoded object from a file
    :loads:   load a tnetstring-encoded object from a string

Note that since parsing a tnetstring requires reading all the data into memory
at once, there's no efficiency gain from using the file-based versions of these
functions.  They're only here so you can use load() to read precisely one
item from a file or socket without consuming any extra data.

The tnetstrings specification explicitly states that strings are binary blobs
and forbids the use of unicode at the protocol level.
**This implementation decodes dictionary keys as surrogate-escaped ASCII**,
all other strings are returned as plain bytes.

:Copyright: (c) 2012-2013 by Ryan Kelly <ryan@rfk.id.au>.
:Copyright: (c) 2014 by Carlo Pires <carlopires@gmail.com>.
:Copyright: (c) 2016 by Maximilian Hils <tnetstring3@maximilianhils.com>.

:License: MIT
"""

from typing import BinaryIO
from typing import Union

TSerializable = Union[None, str, bool, int, float, bytes, list, tuple, dict]


def dumps(value: TSerializable) -> bytes:
    """
    This function dumps a python object as a tnetstring.
    """
    #  This collects output fragments in a list and joins them together
    #  at the end, which is measurably faster than creating all the
    #  intermediate strings and avoids copying large bytes values.
    out: list[bytes] = []
    _dump(out, value)
    return b"".join(out)


def dump(value: TSerializable, file_handle: BinaryIO) -> None:
    """
    This function dumps a python object as a tnetstring and
    writes it to the given file.
    """
    file_handle.write(dumps(value))


def _dump(out: list[bytes], value: TSerializable) -> int:
    """
    Dump value as a tnetstring by appending chunks to out.
    Returns the number of bytes appended.

    The length prefix of a list or dict is only known after its items have been
    dumped, so a placeholder is appended first and filled in afterwards.
    """
    if value is None:
        out.append(b"0:~")
        return 3
    elif value is True:
        out.append(b"4:true!")
        return 7
    elif value is False:
        out.append(b"5:false!")
        return 8
    #  The remaining types are checked roughly in order of how common they are in flows.
    elif isinstance(value, str):
        data = value.encode("utf8")
        chunk = b"%d:%s;" % (len(data), data)
        out.append(chunk)
        return len(chunk)
    elif isinstance(value, bytes):
        span = b"%d:" % len(value)
        out += (span, value, b",")
        return len(span) + len(value) + 1
    elif isinstance(value, (list, tuple)):
        i = len(out)
        out.append(b"")
        size = 0
        for item in value:
            size += _dump(out, item)
        span = b"%d:" % size
        out[i] = span
        out.append(b"]")
        return len(span) + size + 1
    elif isinstance(value, int):
        data = str(value).encode()
        chunk = b"%d:%s#" % (len(data), data)
        out.append(chunk)
        return len(chunk)
    elif isinstance(value, dict):
        i = len(out)
        out.append(b"")
        size = 0
        #  Items are written in reverse order, like earlier versions did.
        for k, v in reversed(value.items()):
            size += _dump(out, k)
            size += _dump(out, v)
        span = b"%d:" % size
        out[i] = span
        out.append(b"}")
        return len(span) + size + 1
    elif isinstance(value, float):
        #  Use repr() for float rather than str().
        #  It round-trips more accurately.
        #  Probably unnecessary in later python versions that
        #  use David Gay's ftoa routines.
        data = repr(value).encode()
        chunk = b"%d:%s^" % (len(data), data)
        out.append(chunk)
        return len(chunk)
    else:
        raise ValueError(f"unserializable object: {value} ({type(value)})")


def loads(string: bytes) -> TSerializable:
    """
    This function parses a tnetstring into a python object.
    """
    data = bytes(string)
    return _pop(data, 0, len(data))[0]


def load(file_handle: BinaryIO) -> TSerializable:
    """load(file) -> object

    This function reads a tnetstring from a file and parses it into a
    python object.  The file must support the read() method, and this
    function promises not to read more data than necessary.
    """
    #  Read the length prefix one char at a time.
    #  Note that the netstring spec explicitly forbids padding zeros.
    c = file_handle.read(1)
    if c == b"":  # we want to detect this special case.
        raise ValueError("not a tnetstring: empty file")
    data_length = b""
    while c.isdigit():
        data_length += c
        if len(data_length) > 12:
            raise ValueError("not a tnetstring: absurdly large length prefix")
        c = file_handle.read(1)
    if c != b":":
        raise ValueError("not a tnetstring: missing or invalid length prefix")

    data = file_handle.read(int(data_length))
    data_type = file_handle.read(1)[0]

    return parse(data_type, data)


def parse(data_type: int, data: bytes | memoryview) -> TSerializable:
    data = bytes(data)
    return _parse(data_type, data, 0, len(data))


def _parse(data_type: int, data: bytes, start: int, end: int) -> TSerializable:
    """
    Parse the value of type data_type stored in data[start:end].

    Nested values are parsed in place by passing offsets around,
    which avoids creating a slice for every element.
    """
    if data_type == 44:  # ord(b",")
        return data[start:end]
    if data_type == 59:  # ord(b";")
        return str(data[start:end], "utf8")
    if data_type == 35:  # ord(b"#")
        try:
            return int(data[start:end])
        except ValueError:
            raise ValueError(
                f"not a tnetstring: invalid integer literal: {data[start:end]!r}"
            )
    if data_type == 94:  # ord(b"^")
        try:
            return float(data[start:end])
        except ValueError:
            raise ValueError(
                f"not a tnetstring: invalid float literal: {data[start:end]!r}"
            )
    if data_type == 33:  # ord(b"!")
        value = data[start:end]
        if value == b"true":
            return True
        elif value == b"false":
            return False
        else:
            raise ValueError(f"not a tnetstring: invalid boolean literal: {value!r}")
    if data_type == 126:  # ord(b"~")
        if end > start:
            raise ValueError(
                f"not a tnetstring: invalid null literal: {data[start:end]!r}"
            )
        return None
    if data_type == 93:  # ord(b"]")
        lst = []
        while start < end:
            item, start = _pop(data, start, end)
            lst.append(item)
        return lst
    if data_type == 125:  # ord(b"}")
        d = {}
        while start < end:
            key, start = _pop(data, start, end)
            val, start = _pop(data, start, end)
            d[key] = val  # type: ignore
        return d
    raise ValueError(f"unknown type tag: {data_type}")


def _pop(data: bytes, start: int, end: int) -> tuple[TSerializable, int]:
    """
    Parse the tnetstring that starts at data[start] and must end before data[end].
    Returns the parsed object and the offset right after it.
    """
    colon = data.find(b":", start, end)
    try:
        if colon < 0:
            raise ValueError
        length = int(data[start:colon])
    except ValueError:
        raise ValueError(
            f"not a tnetstring: missing or invalid length prefix: {data[start:end]!r}"
        )
    value_end = colon + 1 + length
    if length < 0 or value_end >= end:
        #  The data and its type tag must both fit in data[:end].
        raise ValueError(f"not a tnetstring: invalid length prefix: {length}")
    return _parse(data[value_end], data, colon + 1, value_end), value_end + 1


def pop(data: bytes | memoryview) -> tuple[TSerializable, memoryview]:
    """
    This function parses a tnetstring into a python object.
    It returns a tuple giving the parsed object and a string
    containing any unparsed data from the end of the string.
    """
    data = memoryview(data)
    value, end = _pop(bytes(data), 0, len(data))
    return value, data[end:]


__all__ = ["dump", "dumps", "load", "loads", "pop"]
