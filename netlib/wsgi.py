from __future__ import (absolute_import, print_function, division)
import cStringIO, urllib, time, traceback
from . import odict, tcp


class ClientConn:
    def __init__(self, address):
        self.address = tcp.Address.wrap(address)


class Flow:
    def __init__(self, address, request):
        self.client_conn = ClientConn(address)
        self.request = request


class Request:
    def __init__(self, scheme, method, path, headers, content):
        self.scheme, self.method, self.path = scheme, method, path
        self.headers, self.content = headers, content


def date_time_string():
    """Return the current date and time formatted for a message header."""
    WEEKS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    MONTHS = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
            WEEKS[wd],
            day, MONTHS[month], year,
            hh, mm, ss)
    return s


class WSGIAdaptor:
    def __init__(self, app, domain, port, sversion):
        self.app, self.domain, self.port, self.sversion = app, domain, port, sversion

    def make_environ(self, flow, errsoc, **extra):
        if '?' in flow.request.path:
            path_info, query = flow.request.path.split('?', 1)
        else:
            path_info = flow.request.path
            query = ''
        environ = {
            'wsgi.version':         (1, 0),
            'wsgi.url_scheme':      flow.request.scheme,
            'wsgi.input':           cStringIO.StringIO(flow.request.content),
            'wsgi.errors':          errsoc,
            'wsgi.multithread':     True,
            'wsgi.multiprocess':    False,
            'wsgi.run_once':        False,
            'SERVER_SOFTWARE':      self.sversion,
            'REQUEST_METHOD':       flow.request.method,
            'SCRIPT_NAME':          '',
            'PATH_INFO':            urllib.unquote(path_info),
            'QUERY_STRING':         query,
            'CONTENT_TYPE':         flow.request.headers.get('Content-Type', [''])[0],
            'CONTENT_LENGTH':       flow.request.headers.get('Content-Length', [''])[0],
            'SERVER_NAME':          self.domain,
            'SERVER_PORT':          str(self.port),
            # FIXME: We need to pick up the protocol read from the request.
            'SERVER_PROTOCOL':      "HTTP/1.1",
        }
        environ.update(extra)
        if flow.client_conn.address:
            environ["REMOTE_ADDR"], environ["REMOTE_PORT"] = flow.client_conn.address()

        for key, value in flow.request.headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
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
                <pre>%s"</pre>
            </html>
        """%s
        if not headers_sent:
            soc.write("HTTP/1.1 500 Internal Server Error\r\n")
            soc.write("Content-Type: text/html\r\n")
            soc.write("Content-Length: %s\r\n"%len(c))
            soc.write("\r\n")
        soc.write(c)

    def serve(self, request, soc, **env):
        state = dict(
            response_started = False,
            headers_sent = False,
            status = None,
            headers = None
        )
        def write(data):
            if not state["headers_sent"]:
                soc.write("HTTP/1.1 %s\r\n"%state["status"])
                h = state["headers"]
                if 'server' not in h:
                    h["Server"] = [self.sversion]
                if 'date' not in h:
                    h["Date"] = [date_time_string()]
                soc.write(str(h))
                soc.write("\r\n")
                state["headers_sent"] = True
            if data:
                soc.write(data)
            soc.flush()

        def start_response(status, headers, exc_info=None):
            if exc_info:
                try:
                    if state["headers_sent"]:
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None
            elif state["status"]:
                raise AssertionError('Response already started')
            state["status"] = status
            state["headers"] = odict.ODictCaseless(headers)
            return write

        errs = cStringIO.StringIO()
        try:
            dataiter = self.app(self.make_environ(request, errs, **env), start_response)
            for i in dataiter:
                write(i)
            if not state["headers_sent"]:
                write("")
        except Exception:
            try:
                s = traceback.format_exc()
                errs.write(s)
                self.error_page(soc, state["headers_sent"], s)
            except Exception:    # pragma: no cover
                pass
        return errs.getvalue()


