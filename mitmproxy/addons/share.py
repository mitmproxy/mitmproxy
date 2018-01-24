import typing
import random
import datetime
import time
import _io
import http.client

from mitmproxy import command
from mitmproxy import io
from mitmproxy import ctx
from mitmproxy import flow


class Share:
    def encode_multipart_formdata(self, filename, content):
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

    def post_multipart(self, host, filename, content):
        content_type, body = self.encode_multipart_formdata(filename, content)
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

    def base36encode(self, integer):
        chars, encoded = "0123456789abcdefghijklmnopqrstuvwxyz", ""

        while integer > 0:
            integer, remainder = divmod(integer, 36)
            encoded = chars[remainder] + encoded

        return encoded

    @command.command("share.flows")
    def share(self, flows: typing.Sequence[flow.Flow]) -> None:
        d = datetime.datetime.utcnow()
        u_id = self.base36encode(int(time.mktime(d.timetuple()) * 1000 * random.random()))[0:7]
        f = _io.BytesIO()
        stream = io.FlowWriter(f)
        for i in flows:
            stream.add(i)
        f.seek(0)
        content = f.read()
        res = self.post_multipart('upload.share.mitmproxy.org.s3.amazonaws.com', u_id, content)
        f.close()
        ctx.log.alert("%s" % res)
