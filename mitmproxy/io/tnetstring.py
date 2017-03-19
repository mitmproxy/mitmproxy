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

import collections
from typing import io, Union, Tuple

TSerializable = Union[None, bool, int, float, bytes, list, tuple, dict]


def dumps(value: TSerializable) -> bytes:
    """
    This function dumps a python object as a tnetstring.
    """
    #  This uses a deque to collect output fragments in reverse order,
    #  then joins them together at the end.  It's measurably faster
    #  than creating all the intermediate strings.
    q = collections.deque()
    _rdumpq(q, 0, value)
    return b''.join(q)


def dump(value: TSerializable, file_handle: io.BinaryIO) -> None:
    """
    This function dumps a python object as a tnetstring and
    writes it to the given file.
    """
    file_handle.write(dumps(value))


def _rdumpq(q: collections.deque, size: int, value: TSerializable) -> int:
    """
    Dump value as a tnetstring, to a deque instance, last chunks first.

    This function generates the tnetstring representation of the given value,
    pushing chunks of the output onto the given deque instance.  It pushes
    the last chunk first, then recursively generates more chunks.

    When passed in the current size of the string in the queue, it will return
    the new size of the string in the queue.

    Operating last-chunk-first makes it easy to calculate the size written
    for recursive structures without having to build their representation as
    a string.  This is measurably faster than generating the intermediate
    strings, especially on deeply nested structures.
    """
    write = q.appendleft
    if value is None:
        write(b'0:~')
        return size + 3
    elif value is True:
        write(b'4:true!')
        return size + 7
    elif value is False:
        write(b'5:false!')
        return size + 8
    elif isinstance(value, int):
        data = str(value).encode()
        ldata = len(data)
        span = str(ldata).encode()
        write(b'%s:%s#' % (span, data))
        return size + 2 + len(span) + ldata
    elif isinstance(value, float):
        #  Use repr() for float rather than str().
        #  It round-trips more accurately.
        #  Probably unnecessary in later python versions that
        #  use David Gay's ftoa routines.
        data = repr(value).encode()
        ldata = len(data)
        span = str(ldata).encode()
        write(b'%s:%s^' % (span, data))
        return size + 2 + len(span) + ldata
    elif isinstance(value, bytes):
        data = value
        ldata = len(data)
        span = str(ldata).encode()
        write(b',')
        write(data)
        write(b':')
        write(span)
        return size + 2 + len(span) + ldata
    elif isinstance(value, str):
        data = value.encode("utf8")
        ldata = len(data)
        span = str(ldata).encode()
        write(b';')
        write(data)
        write(b':')
        write(span)
        return size + 2 + len(span) + ldata
    elif isinstance(value, (list, tuple)):
        write(b']')
        init_size = size = size + 1
        for item in reversed(value):
            size = _rdumpq(q, size, item)
        span = str(size - init_size).encode()
        write(b':')
        write(span)
        return size + 1 + len(span)
    elif isinstance(value, dict):
        write(b'}')
        init_size = size = size + 1
        for (k, v) in value.items():
            size = _rdumpq(q, size, v)
            size = _rdumpq(q, size, k)
        span = str(size - init_size).encode()
        write(b':')
        write(span)
        return size + 1 + len(span)
    else:
        raise ValueError("unserializable object: {} ({})".format(value, type(value)))


def loads(string: bytes) -> TSerializable:
    """
    This function parses a tnetstring into a python object.
    """
    return pop(string)[0]


def load(file_handle: io.BinaryIO) -> TSerializable:
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
        if len(data_length) > 9:
            raise ValueError("not a tnetstring: absurdly large length prefix")
        c = file_handle.read(1)
    if c != b":":
        raise ValueError("not a tnetstring: missing or invalid length prefix")

    data = file_handle.read(int(data_length))
    data_type = file_handle.read(1)[0]

    return parse(data_type, data)


def parse(data_type: int, data: bytes) -> TSerializable:
    if data_type == ord(b','):
        return data
    if data_type == ord(b';'):
        return data.decode("utf8")
    if data_type == ord(b'#'):
        try:
            return int(data)
        except ValueError:
            raise ValueError("not a tnetstring: invalid integer literal: {}".format(data))
    if data_type == ord(b'^'):
        try:
            return float(data)
        except ValueError:
            raise ValueError("not a tnetstring: invalid float literal: {}".format(data))
    if data_type == ord(b'!'):
        if data == b'true':
            return True
        elif data == b'false':
            return False
        else:
            raise ValueError("not a tnetstring: invalid boolean literal: {}".format(data))
    if data_type == ord(b'~'):
        if data:
            raise ValueError("not a tnetstring: invalid null literal")
        return None
    if data_type == ord(b']'):
        l = []
        while data:
            item, data = pop(data)
            l.append(item)
        return l
    if data_type == ord(b'}'):
        d = {}
        while data:
            key, data = pop(data)
            val, data = pop(data)
            d[key] = val
        return d
    raise ValueError("unknown type tag: {}".format(data_type))


def pop(data: bytes) -> Tuple[TSerializable, bytes]:
    """
    This function parses a tnetstring into a python object.
    It returns a tuple giving the parsed object and a string
    containing any unparsed data from the end of the string.
    """
    #  Parse out data length, type and remaining string.
    try:
        length, data = data.split(b':', 1)
        length = int(length)
    except ValueError:
        raise ValueError("not a tnetstring: missing or invalid length prefix: {}".format(data))
    try:
        data, data_type, remain = data[:length], data[length], data[length + 1:]
    except IndexError:
        #  This fires if len(data) < dlen, meaning we don't need
        #  to further validate that data is the right length.
        raise ValueError("not a tnetstring: invalid length prefix: {}".format(length))
    # Parse the data based on the type tag.
    return parse(data_type, data), remain


__all__ = ["dump", "dumps", "load", "loads", "pop"]
