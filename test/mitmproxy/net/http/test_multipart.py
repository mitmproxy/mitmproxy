import pytest

from mitmproxy.net.http import multipart


def test_decode():
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

    boundary = "boundary茅莽"
    result = multipart.decode_multipart(f"multipart/form-data; {boundary=!s}", content)
    assert result == []

    assert multipart.decode_multipart("", content) == []


def test_decode_preserves_newline_in_value():
    boundary = b"somefancyboundary"

    content = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="field1"\r\n'
        b"\r\n"
        b"hello\nworld\r\n"
        b"--" + boundary + b"--\r\n"
    )

    form = multipart.decode_multipart(
        "multipart/form-data; boundary=somefancyboundary", content
    )

    assert form == [(b"field1", b"hello\nworld")]


def test_encode():
    data = [(b"file", b"shell.jpg"), (b"file_size", b"1000")]
    content = multipart.encode_multipart(
        "multipart/form-data; boundary=127824672498", data
    )

    assert b'Content-Disposition: form-data; name="file"' in content
    assert (
        b"Content-Type: text/plain; charset=utf-8\r\n\r\nshell.jpg\r\n\r\n--127824672498\r\n"
        in content
    )
    assert b"1000\r\n\r\n--127824672498--\r\n"
    assert len(content) == 252

    with pytest.raises(ValueError, match=r"boundary found in encoded string"):
        multipart.encode_multipart(
            "multipart/form-data; boundary=127824672498", [(b"key", b"--127824672498")]
        )

    result = multipart.encode_multipart(
        "multipart/form-data; boundary=boundary茅莽", data
    )
    assert result == b""

    assert multipart.encode_multipart("", data) == b""


def test_decode_skips_malformed_part_without_blank_line():
    boundary = b"somefancyboundary"

    content = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="field1"\r\n'
        b"no blank line separating headers from a value here\r\n"
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="field2"\r\n'
        b"\r\n"
        b"value2\r\n"
        b"--" + boundary + b"--\r\n"
    )

    form = multipart.decode_multipart(
        "multipart/form-data; boundary=somefancyboundary", content
    )

    # The malformed first part (no header/body separator) is skipped rather
    # than raising, and doesn't prevent the well-formed second part from
    # being parsed.
    assert form == [(b"field2", b"value2")]


def test_decode_preserves_trailing_newline_in_value():
    boundary = b"somefancyboundary"

    content = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="field1"\r\n'
        b"\r\n"
        b"hello\nworld\n\r\n"
        b"--" + boundary + b"--\r\n"
    )

    form = multipart.decode_multipart(
        "multipart/form-data; boundary=somefancyboundary",
        content,
    )

    assert form == [(b"field1", b"hello\nworld\n")]
