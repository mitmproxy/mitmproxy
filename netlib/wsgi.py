from __future__ import (absolute_import, print_function, division)
from io import BytesIO, StringIO
import urllib
import time
import traceback

import six
from six.moves import urllib

from netlib.utils import always_bytes, native
from . import http, tcp

class ClientConn(object):

    def __init__(self, address):
        self.address = tcp.Address.wrap(address)


class Flow(object):

    def __init__(self, address, request):
        self.client_conn = ClientConn(address)
        self.request = request


class Request(object):

    def __init__(self, scheme, method, path, http_version, headers, content):
        self.scheme, self.method, self.path = scheme, method, path
        self.headers, self.content = headers, content
        self.http_version = http_version


def date_time_string():
    """Return the current date and time formatted for a message header."""
    WEEKS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    MONTHS = [
        None,
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ]
    now = time.time()
    year, month, day, hh, mm, ss, wd, y_, z_ = time.gmtime(now)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        WEEKS[wd],
        day, MONTHS[month], year,
        hh, mm, ss
    )
    return s


class WSGIAdaptor(object):

    def __init__(self, app, domain, port, sversion):
        self.app, self.domain, self.port, self.sversion = app, domain, port, sversion

    def make_environ(self, flow, errsoc, **extra):
        path = native(flow.request.path, "latin-1")
        if '?' in path:
            path_info, query = native(path, "latin-1").split('?', 1)
        else:
            path_info = path
            query = ''
        environ = {
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': native(flow.request.scheme, "latin-1"),
            'wsgi.input': BytesIO(flow.request.content or b""),
            'wsgi.errors': errsoc,
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'SERVER_SOFTWARE': self.sversion,
            'REQUEST_METHOD': native(flow.request.method, "latin-1"),
            'SCRIPT_NAME': '',
            'PATH_INFO': urllib.parse.unquote(path_info),
            'QUERY_STRING': query,
            'CONTENT_TYPE': native(flow.request.headers.get('Content-Type', ''), "latin-1"),
            'CONTENT_LENGTH': native(flow.request.headers.get('Content-Length', ''), "latin-1"),
            'SERVER_NAME': self.domain,
            'SERVER_PORT': str(self.port),
            'SERVER_PROTOCOL': native(flow.request.http_version, "latin-1"),
        }
        environ.update(extra)
        if flow.client_conn.address:
            environ["REMOTE_ADDR"] = native(flow.client_conn.address.host, "latin-1")
            environ["REMOTE_PORT"] = flow.client_conn.address.port

        for key, value in flow.request.headers.items():
            key = 'HTTP_' + native(key, "latin-1").upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
        return environ

    def error_page(self, soc, headers_sent, s):
        """
            Make a best-effort attempt to write an error page. If headers are
            already sent, we just bung the error into the page.
        """
        c = """
            <html>
                <h1>Internal Server Error</h1>
                <pre>{err}"</pre>
            </html>
        """.format(err=s).strip().encode()

        if not headers_sent:
            soc.write(b"HTTP/1.1 500 Internal Server Error\r\n")
            soc.write(b"Content-Type: text/html\r\n")
            soc.write("Content-Length: {length}\r\n".format(length=len(c)).encode())
            soc.write(b"\r\n")
        soc.write(c)

    def serve(self, request, soc, **env):
        state = dict(
            response_started=False,
            headers_sent=False,
            status=None,
            headers=None
        )

        def write(data):
            if not state["headers_sent"]:
                soc.write("HTTP/1.1 {status}\r\n".format(status=state["status"]).encode())
                headers = state["headers"]
                if 'server' not in headers:
                    headers["Server"] = self.sversion
                if 'date' not in headers:
                    headers["Date"] = date_time_string()
                soc.write(bytes(headers))
                soc.write(b"\r\n")
                state["headers_sent"] = True
            if data:
                soc.write(data)
            soc.flush()

        def start_response(status, headers, exc_info=None):
            if exc_info:
                if state["headers_sent"]:
                    six.reraise(*exc_info)
            elif state["status"]:
                raise AssertionError('Response already started')
            state["status"] = status
            state["headers"] = http.Headers([[always_bytes(k), always_bytes(v)] for k,v in headers])
            if exc_info:
                self.error_page(soc, state["headers_sent"], traceback.format_tb(exc_info[2]))
                state["headers_sent"] = True

        errs = six.BytesIO()
        try:
            dataiter = self.app(
                self.make_environ(request, errs, **env), start_response
            )
            for i in dataiter:
                write(i)
            if not state["headers_sent"]:
                write(b"")
        except Exception as e:
            try:
                s = traceback.format_exc()
                errs.write(s.encode("utf-8", "replace"))
                self.error_page(soc, state["headers_sent"], s)
            except Exception:    # pragma: no cover
                pass
        return errs.getvalue()
