import pytest

from mitmproxy.net.http import multipart


def test_decode_preserves_newlines():
    """Test that decode_multipart preserves \\n and \\r within binary content."""
    boundary = "boundary123"
    # Content with embedded newlines in the value
    content = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="data"\r\n'
        f"Content-Type: text/plain\r\n"
        f"\r\n"
        f"a\nb\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    form = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content
    )
    assert len(form) == 1
    assert form[0] == (b"data", b"a\nb"), f"Expected newline preserved, got {form[0]}"

    # CRLF in content should also be preserved
    content2 = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"\r\n'
        f"\r\n"
        f"line1\r\nline2\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    form2 = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content2
    )
    assert len(form2) == 1
    assert form2[0] == (b"file", b"line1\r\nline2"), \
        f"Expected CRLF preserved, got {form2[0]}"

    # Binary bytes (0x00) should also be preserved
    content3 = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="bin"\r\n'
        f"\r\n"
        + b"binary\x00data\nwith\r\nbytes"
        + f"\r\n--{boundary}--\r\n".encode()
    )

    form3 = multipart.decode_multipart(
        f"multipart/form-data; boundary={boundary}", content3
    )
    assert len(form3) == 1
    assert form3[0] == (b"bin", b"binary\x00data\nwith\r\nbytes"), \
        f"Expected binary data preserved, got {form3[0]}"


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
