from mitmproxy.net.http import Headers
from mitmproxy.net.http import multipart


def test_decode():
    boundary = 'somefancyboundary'
    headers = Headers(
        content_type='multipart/form-data; boundary=' + boundary
    )
    content = (
        "--{0}\n"
        "Content-Disposition: form-data; name=\"field1\"\n\n"
        "value1\n"
        "--{0}\n"
        "Content-Disposition: form-data; name=\"field2\"\n\n"
        "value2\n"
        "--{0}--".format(boundary).encode()
    )

    form = multipart.decode(headers, content)

    assert len(form) == 2
    assert form[0] == (b"field1", b"value1")
    assert form[1] == (b"field2", b"value2")
