import http.client


def encode_multipart_formdata(filename, content):
    params = {"key": filename, "acl": "bucket-owner-full-control", "Content-Type": "application/octet-stream"}
    LIMIT = b'---------------------------198495659117975628761412556003'
    CRLF = b'\r\n'
    l = []
    for (key, value) in params.items():
        l.append(b'--' + LIMIT)
        l.append(b'Content-Disposition: form-data; name="%b"' % key.encode("utf-8"))
        l.append(b'')
        l.append(value.encode("utf-8"))
    l.append(b'--' + LIMIT)
    l.append(b'Content-Disposition: form-data; name="file"; filename="%b"' % filename.encode("utf-8"))
    l.append(b'Content-Type: application/octet-stream')
    l.append(b'')
    l.append(content)
    l.append(b'--' + LIMIT + b'--')
    l.append(b'')
    body = CRLF.join(l)
    content_type = b'multipart/form-data; boundary=%b' % LIMIT
    return content_type, body


def post_multipart(host, filename, content):
    content_type, body = encode_multipart_formdata(filename, content)
    conn = http.client.HTTPConnection(host, 80)
    headers = {'content-type': content_type, 'content-length': str(len(body))}
    try:
        conn.request("POST", "", body, headers)
    except http.client.CannotSendRequest:
        return 'We failed to reach a server.'
    try:
        conn.getresponse()
    except http.client.RemoteDisconnected:
        return 'The server couldn\'t fulfill the request.'
    else:
        conn.close()
        return 'URL: share.mitmproxy.org/%s' % filename
