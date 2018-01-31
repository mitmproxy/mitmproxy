import typing
import random
import string
import io
import http.client

from mitmproxy import command
import mitmproxy.io
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy.net.http import status_codes


class Share:
    def encode_multipart_formdata(self, filename: str, content: bytes) -> typing.Tuple[str, bytes]:
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
        content_type = 'multipart/form-data; boundary=%s' % LIMIT.decode("utf-8")
        return content_type, body

    def post_multipart(self, host: str, filename: str, content: bytes) -> str:
        """
        Upload flows to the specified S3 server.

        Returns:
            - The share URL, if upload is successful.
        Raises:
            - IOError, otherwise.
        """
        content_type, body = self.encode_multipart_formdata(filename, content)
        conn = http.client.HTTPConnection(host)  # FIXME: This ultimately needs to be HTTPSConnection
        headers = {'content-type': content_type}
        try:
            conn.request("POST", "", body, headers)
            resp = conn.getresponse()
        except Exception as v:
            raise IOError(v)
        finally:
            conn.close()
        if resp.status != 204:
            if resp.reason:
                reason = resp.reason
            else:
                reason = status_codes.RESPONSES.get(resp.status, str(resp.status))
            raise IOError(reason)
        return "https://share.mitmproxy.org/%s" % filename

    @command.command("share.flows")
    def share(self, flows: typing.Sequence[flow.Flow]) -> None:
        u_id = "".join(random.choice(string.ascii_lowercase + string.digits)for _ in range(7))
        f = io.BytesIO()
        stream = mitmproxy.io.FlowWriter(f)
        for x in flows:
            stream.add(x)
        f.seek(0)
        content = f.read()
        try:
            res = self.post_multipart('upload.share.mitmproxy.org.s3.amazonaws.com', u_id, content)
        except IOError as v:
            ctx.log.warn("%s" % v)
        else:
            ctx.log.alert("%s" % res)
        finally:
            f.close()