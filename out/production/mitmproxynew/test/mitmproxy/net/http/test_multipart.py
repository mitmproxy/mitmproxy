import pytest

from mitmproxy.http import Headers
from mitmproxy.net.http import multipart


def test_decode():
    boundary = 'somefancyboundary'
    content = (
        "--{0}\n"
        "Content-Disposition: form-data; name=\"field1\"\n\n"
        "value1\n"
        "--{0}\n"
        "Content-Disposition: form-data; name=\"field2\"\n\n"
        "value2\n"
        "--{0}--".format(boundary).encode()
    )
    form = multipart.decode(f'multipart/form-data; boundary={boundary}', content)

    assert len(form) == 2
    assert form[0] == (b"field1", b"value1")
    assert form[1] == (b"field2", b"value2")

    boundary = 'boundary茅莽'
    result = multipart.decode(f'multipart/form-data; boundary={boundary}', content)
    assert result == []

    assert multipart.decode("", content) == []


def test_encode():
    data = [(b"file", b"shell.jpg"),
            (b"file_size", b"1000")]
    headers = Headers(
        content_type='multipart/form-data; boundary=127824672498'
    )
    content = multipart.encode(headers, data)

    assert b'Content-Disposition: form-data; name="file"' in content
    assert b'Content-Type: text/plain; charset=utf-8\r\n\r\nshell.jpg\r\n\r\n--127824672498\r\n' in content
    assert b'1000\r\n\r\n--127824672498--\r\n'
    assert len(content) == 252

    with pytest.raises(ValueError, match=r"boundary found in encoded string"):
        multipart.encode(headers, [(b"key", b"--127824672498")])

    boundary = 'boundary茅莽'
    headers = Headers(
        content_type='multipart/form-data; boundary=' + boundary
    )
    result = multipart.encode(headers, data)
    assert result == b''
