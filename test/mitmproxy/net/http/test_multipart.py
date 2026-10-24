import pytest

from mitmproxy.net.http import multipart


def test_decode():
    boundary = "somefancyboundary"
    content = (
        "--{0}\r\n"
        'Content-Disposition: form-data; name="field1"\r\n\r\n'
        "value1\r\n"
        "--{0}\r\n"
        'Content-Disposition: form-data; name="field2"\r\n\r\n'
        "value2\r\n"
        "--{0}--".format(boundary).encode()
    )
    form = multipart.decode_multipart(f"multipart/form-data; {boundary=!s}", content)

    assert len(form) == 2
    assert form[0] == (b"field1", b"value1")
    assert form[1] == (b"field2", b"value2")

    boundary = "boundary茅莽"
    result = multipart.decode_multipart(f"multipart/form-data; {boundary=!s}", content)
    assert result == []

    assert multipart.decode_multipart("", content) == []


def test_decode_with_lf():
    """Bare LF line endings should also be handled for robustness."""
    boundary = "somefancyboundary"
    content = (
        "--{0}\n"
        'Content-Disposition: form-data; name="field1"\n\n'
        "value1\n"
        "--{0}\n"
        'Content-Disposition: form-data; name="field2"\n\n'
        "value2\n"
        "--{0}--".format(boundary).encode()
    )
    form = multipart.decode_multipart(f"multipart/form-data; {boundary=!s}", content)

    assert len(form) == 2
    assert form[0] == (b"field1", b"value1")
    assert form[1] == (b"field2", b"value2")


def test_decode_content_preserves_newlines():
    """Newlines within field values must be preserved (issue #4466)."""
    boundary = "testboundary"
    content = (
        "--{0}\r\n"
        'Content-Disposition: form-data; name="data"\r\n\r\n'
        "a\r\nb\r\n"
        "--{0}\r\n"
        'Content-Disposition: form-data; name="data2"\r\n\r\n'
        "line1\r\nline2\r\nline3\r\n"
        "--{0}--".format(boundary).encode()
    )
    form = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content
    )
    assert len(form) == 2
    assert form[0] == (b"data", b"a\r\nb")
    assert form[1] == (b"data2", b"line1\r\nline2\r\nline3")


def test_decode_content_preserves_lf_newlines():
    """Bare LF newlines within field values must also be preserved."""
    boundary = "testboundary"
    content = (
        '--{0}\nContent-Disposition: form-data; name="data"\n\na\nb\n--{0}--'.format(
            boundary
        ).encode()
    )
    form = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content
    )
    assert len(form) == 1
    assert form[0] == (b"data", b"a\nb")


def test_decode_binary_content():
    """Binary content with embedded \\r\\n bytes must not be corrupted."""
    boundary = "binboundary"
    # Simulate binary data (e.g. a small JPEG-like payload) that contains
    # 0x0A and 0x0D bytes naturally.
    binary_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\r\n\x00\x01\n\x01"
    content = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test.bin"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        + binary_data
        + b"\r\n--"
        + boundary.encode()
        + b"--"
    )
    form = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content
    )
    assert len(form) == 1
    assert form[0] == (b"file", binary_data)


def test_decode_roundtrip():
    """Encoding and then decoding should recover the field names and values."""
    ct = "multipart/form-data; boundary=roundtripboundary"
    parts = [
        (b"name", b"Alice"),
        (b"message", b"Hello World"),
    ]
    encoded = multipart.encode_multipart(ct, parts)
    decoded = multipart.decode_multipart(ct, encoded)
    assert decoded == parts


def test_encode():
    data = [(b"file", b"shell.jpg"), (b"file_size", b"1000")]
    content = multipart.encode_multipart(
        "multipart/form-data; boundary=127824672498", data
    )

    assert b'Content-Disposition: form-data; name="file"' in content
    assert (
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nshell.jpg\r\n--127824672498\r\n"
        in content
    )
    assert b"1000\r\n--127824672498--\r\n" in content
    assert len(content) == 248

    with pytest.raises(ValueError, match=r"boundary found in encoded string"):
        multipart.encode_multipart(
            "multipart/form-data; boundary=127824672498", [(b"key", b"--127824672498")]
        )

    result = multipart.encode_multipart(
        "multipart/form-data; boundary=boundary茅莽", data
    )
    assert result == b""

    assert multipart.encode_multipart("", data) == b""
