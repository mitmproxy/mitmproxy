from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import mimetypes


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def encode_multipart_formdata(filename, content):
    params = {"key": filename, "acl": "bucket-owner-full-control", "Content-Type": "application/octet-stream"}
    LIMIT = b'---------------------------198495659117975628761412556003'
    CRLF = b'\r\n'
    L = []
    for (key, value) in params.items():
        L.append(b'--' + LIMIT)
        L.append(b'Content-Disposition: form-data; name="%b"' % key.encode("utf-8"))
        L.append(b'')
        L.append(value.encode("utf-8"))
    L.append(b'--' + LIMIT)
    L.append(b'Content-Disposition: form-data; name="file"; filename="%b"' % filename.encode("utf-8"))
    L.append(b'Content-Type: %b' % get_content_type(filename).encode("utf-8"))
    L.append(b'')
    L.append(content)
    L.append(b'--' + LIMIT + b'--')
    L.append(b'')
    body = CRLF.join(L)
    content_type = b'multipart/form-data; boundary=%b' % LIMIT
    return content_type, body

def post_multipart(host, filename, content):
    content_type, body = encode_multipart_formdata(filename, content)
    req = Request("http://upload.share.mitmproxy.org.s3.amazonaws.com", data=body, method='POST')
    req.add_header('content-type', content_type)
    req.add_header('content-length', str(len(body)))
    try:
        response = urlopen(req)
    except HTTPError as e:
        return ('The server couldn\'t fulfill the request.')
    except URLError as e:
        return ('We failed to reach a server.')
    else:
        return ('URL: share.mitmproxy.org/%s' % filename)
