# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    This module provides more sophisticated flow tracking. These match requests
    with their responses, and provide filtering and interception facilities.
"""
import hashlib, Cookie, cookielib, copy, re, urlparse, os
import time, urllib
import tnetstring, filt, script, utils, encoding, proxy
from email.utils import parsedate_tz, formatdate, mktime_tz
from netlib import odict, http, certutils
import controller, version
import app

HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_MISSING = 0

ODict = odict.ODict
ODictCaseless = odict.ODictCaseless


class ReplaceHooks:
    def __init__(self):
        self.lst = []

    def set(self, r):
        self.clear()
        for i in r:
            self.add(*i)

    def add(self, fpatt, rex, s):
        """
            add a replacement hook.

            fpatt: a string specifying a filter pattern.
            rex: a regular expression.
            s: the replacement string

            returns true if hook was added, false if the pattern could not be
            parsed.
        """
        cpatt = filt.parse(fpatt)
        if not cpatt:
            return False
        try:
            re.compile(rex)
        except re.error:
            return False
        self.lst.append((fpatt, rex, s, cpatt))
        return True

    def get_specs(self):
        """
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s) tuples.
        """
        return [i[:3] for i in self.lst]

    def count(self):
        return len(self.lst)

    def run(self, f):
        for _, rex, s, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    f.response.replace(rex, s)
                else:
                    f.request.replace(rex, s)

    def clear(self):
        self.lst = []


class SetHeaders:
    def __init__(self):
        self.lst = []

    def set(self, r):
        self.clear()
        for i in r:
            self.add(*i)

    def add(self, fpatt, header, value):
        """
            Add a set header hook.

            fpatt: String specifying a filter pattern.
            header: Header name.
            value: Header value string

            Returns True if hook was added, False if the pattern could not be
            parsed.
        """
        cpatt = filt.parse(fpatt)
        if not cpatt:
            return False
        self.lst.append((fpatt, header, value, cpatt))
        return True

    def get_specs(self):
        """
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s) tuples.
        """
        return [i[:3] for i in self.lst]

    def count(self):
        return len(self.lst)

    def clear(self):
        self.lst = []

    def run(self, f):
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    del f.response.headers[header]
                else:
                    del f.request.headers[header]
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    f.response.headers.add(header, value)
                else:
                    f.request.headers.add(header, value)


class ScriptContext:
    def __init__(self, master):
        self._master = master

    def log(self, *args, **kwargs):
        """
            Logs an event.

            How this is handled depends on the front-end. mitmdump will display
            events if the eventlog flag ("-e") was passed. mitmproxy sends
            output to the eventlog for display ("v" keyboard shortcut).
        """
        self._master.add_event(*args, **kwargs)

    def duplicate_flow(self, f):
        """
            Returns a duplicate of the specified flow. The flow is also
            injected into the current state, and is ready for editing, replay,
            etc.
        """
        self._master.pause_scripts = True
        f = self._master.duplicate_flow(f)
        self._master.pause_scripts = False
        return f

    def replay_request(self, f):
        """
            Replay the request on the current flow. The response will be added
            to the flow object.
        """
        self._master.replay_request(f)


class decoded(object):
    """

        A context manager that decodes a request, response or error, and then
        re-encodes it with the same encoding after execution of the block.

        Example:

        with decoded(request):
            request.content = request.content.replace("foo", "bar")
    """
    def __init__(self, o):
        self.o = o
        ce = o.headers.get_first("content-encoding")
        if ce in encoding.ENCODINGS:
            self.ce = ce
        else:
            self.ce = None

    def __enter__(self):
        if self.ce:
            self.o.decode()

    def __exit__(self, type, value, tb):
        if self.ce:
            self.o.encode(self.ce)


class StateObject:
    def __eq__(self, other):
        try:
            return self._get_state() == other._get_state()
        except AttributeError:
            return False


class HTTPMsg(StateObject):
    def get_decoded_content(self):
        """
            Returns the decoded content based on the current Content-Encoding header.
            Doesn't change the message iteself or its headers.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return self.content
        return encoding.decode(ce, self.content)

    def decode(self):
        """
            Decodes content based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return
        self.content = encoding.decode(
            ce,
            self.content
        )
        del self.headers["content-encoding"]

    def encode(self, e):
        """
            Encodes content with the encoding e, where e is "gzip", "deflate"
            or "identity".
        """
        # FIXME: Error if there's an existing encoding header?
        self.content = encoding.encode(e, self.content)
        self.headers["content-encoding"] = [e]

    def size(self, **kwargs):
        """
            Size in bytes of a fully rendered message, including headers and
            HTTP lead-in.
        """
        hl = len(self._assemble_head(**kwargs))
        if self.content:
            return hl + len(self.content)
        else:
            return hl

    def get_content_type(self):
        return self.headers.get_first("content-type")

    def get_transmitted_size(self):
        # FIXME: this is inprecise in case chunking is used
        # (we should count the chunking headers)
        if not self.content:
            return 0
        return len(self.content)


class Request(HTTPMsg):
    """
        An HTTP request.

        Exposes the following attributes:

            client_conn: ClientConnect object, or None if this is a replay.

            headers: ODictCaseless object

            content: Content of the request, None, or CONTENT_MISSING if there
            is content associated, but not present. CONTENT_MISSING evaluates
            to False to make checking for the presence of content natural.

            scheme: URL scheme (http/https)

            host: Host portion of the URL

            port: Destination port

            path: Path portion of the URL

            timestamp_start: Seconds since the epoch signifying request transmission started

            method: HTTP method

            timestamp_end: Seconds since the epoch signifying request transmission ended

            tcp_setup_timestamp: Seconds since the epoch signifying remote TCP connection setup completion time
            (or None, if request didn't results TCP setup)

            ssl_setup_timestamp: Seconds since the epoch signifying remote SSL encryption setup completion time
            (or None, if request didn't results SSL setup)

    """
    def __init__(self, client_conn, httpversion, host, port, scheme, method, path, headers, content, timestamp_start=None, timestamp_end=None, tcp_setup_timestamp=None, ssl_setup_timestamp=None):
        assert isinstance(headers, ODictCaseless)
        self.client_conn = client_conn
        self.httpversion = httpversion
        self.host, self.port, self.scheme = host, port, scheme
        self.method, self.path, self.headers, self.content = method, path, headers, content
        self.timestamp_start = timestamp_start or utils.timestamp()
        self.timestamp_end = max(timestamp_end or utils.timestamp(), timestamp_start)
        self.close = False
        self.tcp_setup_timestamp = tcp_setup_timestamp
        self.ssl_setup_timestamp = ssl_setup_timestamp

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False

    def anticache(self):
        """
            Modifies this request to remove headers that might produce a cached
            response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            "if-modified-since",
            "if-none-match",
        ]
        for i in delheaders:
            del self.headers[i]

    def anticomp(self):
        """
            Modifies this request to remove headers that will compress the
            resource's data.
        """
        self.headers["accept-encoding"] = ["identity"]

    def constrain_encoding(self):
        """
            Limits the permissible Accept-Encoding values, based on what we can
            decode appropriately.
        """
        if self.headers["accept-encoding"]:
            self.headers["accept-encoding"] = [', '.join(
                e for e in encoding.ENCODINGS if e in self.headers["accept-encoding"][0]
            )]

    def _set_replay(self):
        self.client_conn = None

    def is_replay(self):
        """
            Is this request a replay?
        """
        if self.client_conn:
            return False
        else:
            return True

    def _load_state(self, state):
        if state["client_conn"]:
            if self.client_conn:
                self.client_conn._load_state(state["client_conn"])
            else:
                self.client_conn = ClientConnect._from_state(state["client_conn"])
        else:
            self.client_conn = None
        self.host = state["host"]
        self.port = state["port"]
        self.scheme = state["scheme"]
        self.method = state["method"]
        self.path = state["path"]
        self.headers = ODictCaseless._from_state(state["headers"])
        self.content = state["content"]
        self.timestamp_start = state["timestamp_start"]
        self.timestamp_end = state["timestamp_end"]
        self.tcp_setup_timestamp = state["tcp_setup_timestamp"]
        self.ssl_setup_timestamp = state["ssl_setup_timestamp"]

    def _get_state(self):
        return dict(
            client_conn = self.client_conn._get_state() if self.client_conn else None,
            httpversion = self.httpversion,
            host = self.host,
            port = self.port,
            scheme = self.scheme,
            method = self.method,
            path = self.path,
            headers = self.headers._get_state(),
            content = self.content,
            timestamp_start = self.timestamp_start,
            timestamp_end = self.timestamp_end,
            tcp_setup_timestamp = self.tcp_setup_timestamp,
            ssl_setup_timestamp = self.ssl_setup_timestamp
        )

    @classmethod
    def _from_state(klass, state):
        return klass(
            ClientConnect._from_state(state["client_conn"]),
            tuple(state["httpversion"]),
            str(state["host"]),
            state["port"],
            str(state["scheme"]),
            str(state["method"]),
            str(state["path"]),
            ODictCaseless._from_state(state["headers"]),
            state["content"],
            state["timestamp_start"],
            state["timestamp_end"],
            state["tcp_setup_timestamp"],
            state["ssl_setup_timestamp"]
        )

    def __hash__(self):
        return id(self)

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.content and self.headers.in_any("content-type", HDR_FORM_URLENCODED, True):
            return ODict(utils.urldecode(self.content))
        return ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        # FIXME: If there's an existing content-type header indicating a
        # url-encoded form, leave it alone.
        self.headers["Content-Type"] = [HDR_FORM_URLENCODED]
        self.content = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urlparse.urlparse(self.get_url())
        return [urllib.unquote(i) for i in path.split("/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.quote(i, safe="") for i in lst]
        path = "/" + "/".join(lst)
        scheme, netloc, _, params, query, fragment = urlparse.urlparse(self.get_url())
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_query(self):
        """
            Gets the request query string. Returns an ODict object.
        """
        _, _, _, _, query, _ = urlparse.urlparse(self.get_url())
        if query:
            return ODict(utils.urldecode(query))
        return ODict([])

    def set_query(self, odict):
        """
            Takes an ODict object, and sets the request query string.
        """
        scheme, netloc, path, params, _, fragment = urlparse.urlparse(self.get_url())
        query = utils.urlencode(odict.lst)
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_url(self, hostheader=False):
        """
            Returns a URL string, constructed from the Request's URL compnents.

            If hostheader is True, we use the value specified in the request
            Host header to construct the URL.
        """
        if hostheader:
            host = self.headers.get_first("host") or self.host
        else:
            host = self.host
        host = host.encode("idna")
        return utils.unparse_url(self.scheme, host, self.port, self.path).encode('ascii')

    def set_url(self, url):
        """
            Parses a URL specification, and updates the Request's information
            accordingly.

            Returns False if the URL was invalid, True if the request succeeded.
        """
        parts = http.parse_url(url)
        if not parts:
            return False
        self.scheme, self.host, self.port, self.path = parts
        return True

    def get_cookies(self):
        cookie_headers = self.headers.get("cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookies.extend((pair[0],(pair[2],{})) for pair in pairs)
        return dict(cookies)

    def get_header_size(self):
        FMT = '%s %s HTTP/%s.%s\r\n%s\r\n'
        assembled_header = FMT % (
                self.method,
                self.path,
                self.httpversion[0],
                self.httpversion[1],
                str(self.headers)
            )
        return len(assembled_header)

    def _assemble_head(self, proxy=False):
        FMT = '%s %s HTTP/%s.%s\r\n%s\r\n'
        FMT_PROXY = '%s %s://%s:%s%s HTTP/%s.%s\r\n%s\r\n'

        headers = self.headers.copy()
        utils.del_all(
            headers,
            [
                'proxy-connection',
                'keep-alive',
                'connection',
                'transfer-encoding'
            ]
        )
        if not 'host' in headers:
            headers["host"] = [utils.hostport(self.scheme, self.host, self.port)]
        content = self.content
        if content:
            headers["Content-Length"] = [str(len(content))]
        else:
            content = ""
        if self.close:
            headers["connection"] = ["close"]
        if not proxy:
            return FMT % (
                self.method,
                self.path,
                self.httpversion[0],
                self.httpversion[1],
                str(headers)
            )
        else:
            return FMT_PROXY % (
                self.method,
                self.scheme,
                self.host,
                self.port,
                self.path,
                self.httpversion[0],
                self.httpversion[1],
                str(headers)
            )

    def _assemble(self, _proxy = False):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.

            Returns None if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            return None
        head = self._assemble_head(_proxy)
        if self.content:
            return head + self.content
        else:
            return head

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = utils.safe_subn(pattern, repl, self.content, *args, **kwargs)
        self.path, pc = utils.safe_subn(pattern, repl, self.path, *args, **kwargs)
        c += pc
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c


class Response(HTTPMsg):
    """
        An HTTP response.

        Exposes the following attributes:

            request: Request object.

            code: HTTP response code

            msg: HTTP response message

            headers: ODict object

            content: Content of the request, None, or CONTENT_MISSING if there
            is content associated, but not present. CONTENT_MISSING evaluates
            to False to make checking for the presence of content natural.

            timestamp_start: Seconds since the epoch signifying response transmission started

            timestamp_end: Seconds since the epoch signifying response transmission ended
    """
    def __init__(self, request, httpversion, code, msg, headers, content, cert, timestamp_start=None, timestamp_end=None):
        assert isinstance(headers, ODictCaseless)
        self.request = request
        self.httpversion, self.code, self.msg = httpversion, code, msg
        self.headers, self.content = headers, content
        self.cert = cert
        self.timestamp_start = timestamp_start or utils.timestamp()
        self.timestamp_end = max(timestamp_end or utils.timestamp(), timestamp_start)
        self.replay = False

    def _refresh_cookie(self, c, delta):
        """
            Takes a cookie string c and a time delta in seconds, and returns
            a refreshed cookie string.
        """
        c = Cookie.SimpleCookie(str(c))
        for i in c.values():
            if "expires" in i:
                d = parsedate_tz(i["expires"])
                if d:
                    d = mktime_tz(d) + delta
                    i["expires"] = formatdate(d)
                else:
                    # This can happen when the expires tag is invalid.
                    # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                    # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                    # strictly correct according tot he cookie spec. Browsers
                    # appear to parse this tolerantly - maybe we should too.
                    # For now, we just ignore this.
                    del i["expires"]
        return c.output(header="").strip()

    def refresh(self, now=None):
        """
            This fairly complex and heuristic function refreshes a server
            response for replay.

                - It adjusts date, expires and last-modified headers.
                - It adjusts cookie expiration.
        """
        if not now:
            now = time.time()
        delta = now - self.timestamp_start
        refresh_headers = [
            "date",
            "expires",
            "last-modified",
        ]
        for i in refresh_headers:
            if i in self.headers:
                d = parsedate_tz(self.headers[i][0])
                if d:
                    new = mktime_tz(d) + delta
                    self.headers[i] = [formatdate(new)]
        c = []
        for i in self.headers["set-cookie"]:
            c.append(self._refresh_cookie(i, delta))
        if c:
            self.headers["set-cookie"] = c

    def _set_replay(self):
        self.replay = True

    def is_replay(self):
        """
            Is this response a replay?
        """
        return self.replay

    def _load_state(self, state):
        self.code = state["code"]
        self.msg = state["msg"]
        self.headers = ODictCaseless._from_state(state["headers"])
        self.content = state["content"]
        self.timestamp_start = state["timestamp_start"]
        self.timestamp_end = state["timestamp_end"]
        self.cert = certutils.SSLCert.from_pem(state["cert"]) if state["cert"] else None

    def _get_state(self):
        return dict(
            httpversion = self.httpversion,
            code = self.code,
            msg = self.msg,
            headers = self.headers._get_state(),
            timestamp_start = self.timestamp_start,
            timestamp_end = self.timestamp_end,
            cert = self.cert.to_pem() if self.cert else None,
            content = self.content,
        )

    @classmethod
    def _from_state(klass, request, state):
        return klass(
            request,
            state["httpversion"],
            state["code"],
            str(state["msg"]),
            ODictCaseless._from_state(state["headers"]),
            state["content"],
            certutils.SSLCert.from_pem(state["cert"]) if state["cert"] else None,
            state["timestamp_start"],
            state["timestamp_end"],
        )

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def _assemble_head(self):
        FMT = '%s\r\n%s\r\n'
        headers = self.headers.copy()
        utils.del_all(
            headers,
            ['proxy-connection', 'transfer-encoding']
        )
        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        proto = "HTTP/%s.%s %s %s"%(self.httpversion[0], self.httpversion[1], self.code, str(self.msg))
        data = (proto, str(headers))
        return FMT%data

    def _assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.

            Returns None if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            return None
        head = self._assemble_head()
        if self.content:
            return head + self.content
        else:
            return head

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the response. Encoded content will be decoded
            before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = utils.safe_subn(pattern, repl, self.content, *args, **kwargs)
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c

    def get_header_size(self):
        FMT = '%s\r\n%s\r\n'
        proto = "HTTP/%s.%s %s %s"%(self.httpversion[0], self.httpversion[1], self.code, str(self.msg))
        assembled_header = FMT % (proto, str(self.headers))
        return len(assembled_header)

    def get_cookies(self):
        cookie_headers = self.headers.get("set-cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookie_name = pairs[0][0] # the key of the first key/value pairs
            cookie_value = pairs[0][2] # the value of the first key/value pairs
            cookie_parameters = {key.strip().lower():value.strip() for key,sep,value in pairs[1:]}
            cookies.append((cookie_name, (cookie_value, cookie_parameters)))
        return dict(cookies)

class ClientDisconnect:
    """
        A client disconnection event.

        Exposes the following attributes:

            client_conn: ClientConnect object.
    """
    def __init__(self, client_conn):
        self.client_conn = client_conn


class ClientConnect(StateObject):
    """
        A single client connection. Each connection can result in multiple HTTP
        Requests.

        Exposes the following attributes:

            address: (address, port) tuple, or None if the connection is replayed.
            requestcount: Number of requests created by this client connection.
            close: Is the client connection closed?
            error: Error string or None.
    """
    def __init__(self, address):
        """
            address is an (address, port) tuple, or None if this connection has
            been replayed from within mitmproxy.
        """
        self.address = address
        self.close = False
        self.requestcount = 0
        self.error = None

    def __str__(self):
        if self.address:
            return "%s:%d"%(self.address[0],self.address[1])

    def _load_state(self, state):
        self.close = True
        self.error = state["error"]
        self.requestcount = state["requestcount"]

    def _get_state(self):
        return dict(
            address = list(self.address),
            requestcount = self.requestcount,
            error = self.error,
        )

    @classmethod
    def _from_state(klass, state):
        if state:
            k = klass(state["address"])
            k._load_state(state)
            return k
        else:
            return None

    def copy(self):
        return copy.copy(self)


class Error(StateObject):
    """
        An Error.

        This is distinct from an HTTP error response (say, a code 500), which
        is represented by a normal Response object. This class is responsible
        for indicating errors that fall outside of normal HTTP communications,
        like interrupted connections, timeouts, protocol errors.

        Exposes the following attributes:

            request: Request object
            msg: Message describing the error
            timestamp: Seconds since the epoch
    """
    def __init__(self, request, msg, timestamp=None):
        self.request, self.msg = request, msg
        self.timestamp = timestamp or utils.timestamp()

    def _load_state(self, state):
        self.msg = state["msg"]
        self.timestamp = state["timestamp"]

    def copy(self):
        c = copy.copy(self)
        return c

    def _get_state(self):
        return dict(
            msg = self.msg,
            timestamp = self.timestamp,
        )

    @classmethod
    def _from_state(klass, request, state):
        return klass(
            request,
            state["msg"],
            state["timestamp"],
        )

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Returns the number of replacements
            made.

            FIXME: Is replace useful on an Error object??
        """
        self.msg, c = utils.safe_subn(pattern, repl, self.msg, *args, **kwargs)
        return c


class ClientPlaybackState:
    def __init__(self, flows, exit):
        self.flows, self.exit = flows, exit
        self.current = None

    def count(self):
        return len(self.flows)

    def done(self):
        if len(self.flows) == 0 and not self.current:
            return True
        return False

    def clear(self, flow):
        """
           A request has returned in some way - if this is the one we're
           servicing, go to the next flow.
        """
        if flow is self.current:
            self.current = None

    def tick(self, master, testing=False):
        """
            testing: Disables actual replay for testing.
        """
        if self.flows and not self.current:
            n = self.flows.pop(0)
            n.request.reply = controller.DummyReply()
            n.request.client_conn = None
            self.current = master.handle_request(n.request)
            if not testing and not self.current.response:
                master.replay_request(self.current) # pragma: no cover
            elif self.current.response:
                master.handle_response(self.current.response)


class ServerPlaybackState:
    def __init__(self, headers, flows, exit, nopop):
        """
            headers: Case-insensitive list of request headers that should be
            included in request-response matching.
        """
        self.headers, self.exit, self.nopop = headers, exit, nopop
        self.fmap = {}
        for i in flows:
            if i.response:
                l = self.fmap.setdefault(self._hash(i), [])
                l.append(i)

    def count(self):
        return sum(len(i) for i in self.fmap.values())

    def _hash(self, flow):
        """
            Calculates a loose hash of the flow request.
        """
        r = flow.request
        key = [
            str(r.host),
            str(r.port),
            str(r.scheme),
            str(r.method),
            str(r.path),
            str(r.content),
        ]
        if self.headers:
            hdrs = []
            for i in self.headers:
                v = r.headers[i]
                # Slightly subtle: we need to convert everything to strings
                # to prevent a mismatch between unicode/non-unicode.
                v = [str(x) for x in v]
                hdrs.append((i, v))
            key.append(repr(hdrs))
        return hashlib.sha256(repr(key)).digest()

    def next_flow(self, request):
        """
            Returns the next flow object, or None if no matching flow was
            found.
        """
        l = self.fmap.get(self._hash(request))
        if not l:
            return None

        if self.nopop:
            return l[0]
        else:
            return l.pop(0)



class StickyCookieState:
    def __init__(self, flt):
        """
            flt: Compiled filter.
        """
        self.jar = {}
        self.flt = flt

    def ckey(self, m, f):
        """
            Returns a (domain, port, path) tuple.
        """
        return (
            m["domain"] or f.request.host,
            f.request.port,
            m["path"] or "/"
        )

    def domain_match(self, a, b):
        if cookielib.domain_match(a, b):
            return True
        elif cookielib.domain_match(a, b.strip(".")):
            return True
        return False

    def handle_response(self, f):
        for i in f.response.headers["set-cookie"]:
            # FIXME: We now know that Cookie.py screws up some cookies with
            # valid RFC 822/1123 datetime specifications for expiry. Sigh.
            c = Cookie.SimpleCookie(str(i))
            m = c.values()[0]
            k = self.ckey(m, f)
            if self.domain_match(f.request.host, k[0]):
                self.jar[self.ckey(m, f)] = m

    def handle_request(self, f):
        l = []
        if f.match(self.flt):
            for i in self.jar.keys():
                match = [
                    self.domain_match(f.request.host, i[0]),
                    f.request.port == i[1],
                    f.request.path.startswith(i[2])
                ]
                if all(match):
                    l.append(self.jar[i].output(header="").strip())
        if l:
            f.request.stickycookie = True
            f.request.headers["cookie"] = l


class StickyAuthState:
    def __init__(self, flt):
        """
            flt: Compiled filter.
        """
        self.flt = flt
        self.hosts = {}

    def handle_request(self, f):
        if "authorization" in f.request.headers:
            self.hosts[f.request.host] = f.request.headers["authorization"]
        elif f.match(self.flt):
            if f.request.host in self.hosts:
                f.request.headers["authorization"] = self.hosts[f.request.host]


class Flow:
    """
        A Flow is a collection of objects representing a single HTTP
        transaction. The main attributes are:

            request: Request object
            response: Response object
            error: Error object

        Note that it's possible for a Flow to have both a response and an error
        object. This might happen, for instance, when a response was received
        from the server, but there was an error sending it back to the client.

        The following additional attributes are exposed:

            intercepting: Is this flow currently being intercepted?
    """
    def __init__(self, request):
        self.request = request
        self.response, self.error = None, None
        self.intercepting = False
        self._backup = None

    def copy(self):
        rc = self.request.copy()
        f = Flow(rc)
        if self.response:
            f.response = self.response.copy()
            f.response.request = rc
        if self.error:
            f.error = self.error.copy()
            f.error.request = rc
        return f

    @classmethod
    def _from_state(klass, state):
        f = klass(None)
        f._load_state(state)
        return f

    def _get_state(self):
        d = dict(
            request = self.request._get_state() if self.request else None,
            response = self.response._get_state() if self.response else None,
            error = self.error._get_state() if self.error else None,
            version = version.IVERSION
        )
        return d

    def _load_state(self, state):
        if self.request:
            self.request._load_state(state["request"])
        else:
            self.request = Request._from_state(state["request"])

        if state["response"]:
            if self.response:
                self.response._load_state(state["response"])
            else:
                self.response = Response._from_state(self.request, state["response"])
        else:
            self.response = None

        if state["error"]:
            if self.error:
                self.error._load_state(state["error"])
            else:
                self.error = Error._from_state(self.request, state["error"])
        else:
            self.error = None

    def modified(self):
        """
            Has this Flow been modified?
        """
        # FIXME: Save a serialization in backup, compare current with
        # backup to detect if flow has _really_ been modified.
        if self._backup:
            return True
        else:
            return False

    def backup(self, force=False):
        """
            Save a backup of this Flow, which can be reverted to using a
            call to .revert().
        """
        if not self._backup:
            self._backup = self._get_state()

    def revert(self):
        """
            Revert to the last backed up state.
        """
        if self._backup:
            self._load_state(self._backup)
            self._backup = None

    def match(self, f):
        """
            Match this flow against a compiled filter expression. Returns True
            if matched, False if not.

            If f is a string, it will be compiled as a filter expression. If
            the expression is invalid, ValueError is raised.
        """
        if isinstance(f, basestring):
            f = filt.parse(f)
            if not f:
                raise ValueError("Invalid filter expression.")
        if f:
            return f(self)
        return True

    def kill(self, master):
        """
            Kill this request.
        """
        self.error = Error(self.request, "Connection killed")
        self.error.reply = controller.DummyReply()
        if self.request and not self.request.reply.acked:
            self.request.reply(proxy.KILL)
        elif self.response and not self.response.reply.acked:
            self.response.reply(proxy.KILL)
        master.handle_error(self.error)
        self.intercepting = False

    def intercept(self):
        """
            Intercept this Flow. Processing will stop until accept_intercept is
            called.
        """
        self.intercepting = True

    def accept_intercept(self):
        """
            Continue with the flow - called after an intercept().
        """
        if self.request:
            if not self.request.reply.acked:
                self.request.reply()
            elif self.response and not self.response.reply.acked:
                self.response.reply()
            self.intercepting = False

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in all parts of the
            flow. Encoded content will be decoded before replacement, and
            re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = self.request.replace(pattern, repl, *args, **kwargs)
        if self.response:
            c += self.response.replace(pattern, repl, *args, **kwargs)
        if self.error:
            c += self.error.replace(pattern, repl, *args, **kwargs)
        return c


class State(object):
    def __init__(self):
        self._flow_map = {}
        self._flow_list = []
        self.view = []

        # These are compiled filt expressions:
        self._limit = None
        self.intercept = None
        self._limit_txt = None

    @property
    def limit_txt(self):
        return self._limit_txt

    def flow_count(self):
        return len(self._flow_map)

    def index(self, f):
        return self._flow_list.index(f)

    def active_flow_count(self):
        c = 0
        for i in self._flow_list:
            if not i.response and not i.error:
                c += 1
        return c

    def add_request(self, req):
        """
            Add a request to the state. Returns the matching flow.
        """
        f = Flow(req)
        self._flow_list.append(f)
        self._flow_map[req] = f
        assert len(self._flow_list) == len(self._flow_map)
        if f.match(self._limit):
            self.view.append(f)
        return f

    def add_response(self, resp):
        """
            Add a response to the state. Returns the matching flow.
        """
        f = self._flow_map.get(resp.request)
        if not f:
            return False
        f.response = resp
        if f.match(self._limit) and not f in self.view:
            self.view.append(f)
        return f

    def add_error(self, err):
        """
            Add an error response to the state. Returns the matching flow, or
            None if there isn't one.
        """
        f = self._flow_map.get(err.request)
        if not f:
            return None
        f.error = err
        if f.match(self._limit) and not f in self.view:
            self.view.append(f)
        return f

    def load_flows(self, flows):
        self._flow_list.extend(flows)
        for i in flows:
            self._flow_map[i.request] = i
        self.recalculate_view()

    def set_limit(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self._limit = f
            self._limit_txt = txt
        else:
            self._limit = None
            self._limit_txt = None
        self.recalculate_view()

    def set_intercept(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self.intercept = f
            self.intercept_txt = txt
        else:
            self.intercept = None
            self.intercept_txt = None

    def recalculate_view(self):
        if self._limit:
            self.view = [i for i in self._flow_list if i.match(self._limit)]
        else:
            self.view = self._flow_list[:]

    def delete_flow(self, f):
        if f.request in self._flow_map:
            del self._flow_map[f.request]
        self._flow_list.remove(f)
        if f in self.view:
            self.view.remove(f)
        return True

    def clear(self):
        for i in self._flow_list[:]:
            self.delete_flow(i)

    def accept_all(self):
        for i in self._flow_list[:]:
            i.accept_intercept()

    def revert(self, f):
        f.revert()

    def killall(self, master):
        for i in self._flow_list:
            i.kill(master)


class FlowMaster(controller.Master):
    def __init__(self, server, state):
        controller.Master.__init__(self, server)
        self.state = state
        self.server_playback = None
        self.client_playback = None
        self.kill_nonreplay = False
        self.script = None
        self.pause_scripts = False

        self.stickycookie_state = False
        self.stickycookie_txt = None

        self.stickyauth_state = False
        self.stickyauth_txt = None

        self.anticache = False
        self.anticomp = False
        self.refresh_server_playback = False
        self.replacehooks = ReplaceHooks()
        self.setheaders = SetHeaders()

        self.stream = None
        app.mapp.config["PMASTER"] = self

    def add_event(self, e, level="info"):
        """
            level: info, error
        """
        pass

    def get_script(self, path):
        """
            Returns an (error, script) tuple.
        """
        s = script.Script(path, ScriptContext(self))
        try:
            s.load()
        except script.ScriptError, v:
            return (v.args[0], None)
        ret = s.run("start")
        if not ret[0] and ret[1]:
            return ("Error in script start:\n\n" + ret[1][1], None)
        return (None, s)

    def load_script(self, path):
        """
            Loads a script. Returns an error description if something went
            wrong. If path is None, the current script is terminated.
        """
        if path is None:
            self.run_script_hook("done")
            self.script = None
        else:
            r = self.get_script(path)
            if r[0]:
                return r[0]
            else:
                if self.script:
                    self.run_script_hook("done")
                self.script = r[1]

    def set_stickycookie(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickycookie_state = StickyCookieState(flt)
            self.stickycookie_txt = txt
        else:
            self.stickycookie_state = None
            self.stickycookie_txt = None

    def set_stickyauth(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickyauth_state = StickyAuthState(flt)
            self.stickyauth_txt = txt
        else:
            self.stickyauth_state = None
            self.stickyauth_txt = None

    def start_client_playback(self, flows, exit):
        """
            flows: List of flows.
        """
        self.client_playback = ClientPlaybackState(flows, exit)

    def stop_client_playback(self):
        self.client_playback = None

    def start_server_playback(self, flows, kill, headers, exit, nopop):
        """
            flows: List of flows.
            kill: Boolean, should we kill requests not part of the replay?
        """
        self.server_playback = ServerPlaybackState(headers, flows, exit, nopop)
        self.kill_nonreplay = kill

    def stop_server_playback(self):
        if self.server_playback.exit:
            self.shutdown()
        self.server_playback = None

    def do_server_playback(self, flow):
        """
            This method should be called by child classes in the handle_request
            handler. Returns True if playback has taken place, None if not.
        """
        if self.server_playback:
            rflow = self.server_playback.next_flow(flow)
            if not rflow:
                return None
            response = Response._from_state(flow.request, rflow.response._get_state())
            response._set_replay()
            flow.response = response
            if self.refresh_server_playback:
                response.refresh()
            flow.request.reply(response)
            if self.server_playback.count() == 0:
                self.stop_server_playback()
            return True
        return None

    def tick(self, q):
        if self.client_playback:
            e = [
                self.client_playback.done(),
                self.client_playback.exit,
                self.state.active_flow_count() == 0
            ]
            if all(e):
                self.shutdown()
            self.client_playback.tick(self)

        return controller.Master.tick(self, q)

    def duplicate_flow(self, f):
        return self.load_flow(f.copy())

    def load_flow(self, f):
        """
            Loads a flow, and returns a new flow object.
        """
        if f.request:
            f.request.reply = controller.DummyReply()
            fr = self.handle_request(f.request)
        if f.response:
            f.response.reply = controller.DummyReply()
            self.handle_response(f.response)
        if f.error:
            f.error.reply = controller.DummyReply()
            self.handle_error(f.error)
        return fr

    def load_flows(self, fr):
        """
            Load flows from a FlowReader object.
        """
        for i in fr.stream():
            self.load_flow(i)

    def process_new_request(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_request(f)
        if self.stickyauth_state:
            self.stickyauth_state.handle_request(f)

        if self.anticache:
            f.request.anticache()
        if self.anticomp:
            f.request.anticomp()

        if self.server_playback:
            pb = self.do_server_playback(f)
            if not pb:
                if self.kill_nonreplay:
                    f.kill(self)
                else:
                    f.request.reply()

    def process_new_response(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_response(f)

    def replay_request(self, f, block=False):
        """
            Returns None if successful, or error message if not.
        """
        if f.intercepting:
            return "Can't replay while intercepting..."
        if f.request.content == CONTENT_MISSING:
            return "Can't replay request with missing content..."
        if f.request:
            f.request._set_replay()
            if f.request.content:
                f.request.headers["Content-Length"] = [str(len(f.request.content))]
            f.response = None
            f.error = None
            self.process_new_request(f)
            rt = proxy.RequestReplayThread(
                    self.server.config,
                    f,
                    self.masterq,
                )
            rt.start() # pragma: no cover
            if block:
                rt.join()

    def run_script_hook(self, name, *args, **kwargs):
        if self.script and not self.pause_scripts:
            ret = self.script.run(name, *args, **kwargs)
            if not ret[0] and ret[1]:
                e = "Script error:\n" + ret[1][1]
                self.add_event(e, "error")

    def handle_clientconnect(self, cc):
        self.run_script_hook("clientconnect", cc)
        cc.reply()

    def handle_clientdisconnect(self, r):
        self.run_script_hook("clientdisconnect", r)
        r.reply()

    def handle_error(self, r):
        f = self.state.add_error(r)
        if f:
            self.run_script_hook("error", f)
        if self.client_playback:
            self.client_playback.clear(f)
        r.reply()
        return f

    def handle_request(self, r):
        f = self.state.add_request(r)
        self.replacehooks.run(f)
        self.setheaders.run(f)
        self.run_script_hook("request", f)
        self.process_new_request(f)
        return f

    def handle_response(self, r):
        f = self.state.add_response(r)
        if f:
            self.replacehooks.run(f)
            self.setheaders.run(f)
            self.run_script_hook("response", f)
            if self.client_playback:
                self.client_playback.clear(f)
            self.process_new_response(f)
            if self.stream:
                self.stream.add(f)
        else:
            r.reply()
        return f

    def shutdown(self):
        if self.script:
            self.load_script(None)
        controller.Master.shutdown(self)
        if self.stream:
            for i in self.state._flow_list:
                if not i.response:
                    self.stream.add(i)
            self.stop_stream()

    def start_stream(self, fp, filt):
        self.stream = FilteredFlowWriter(fp, filt)

    def stop_stream(self):
        self.stream.fo.close()
        self.stream = None



class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, flow):
        d = flow._get_state()
        tnetstring.dump(d, self.fo)


class FlowReadError(Exception):
    @property
    def strerror(self):
        return self.args[0]


class FlowReader:
    def __init__(self, fo):
        self.fo = fo

    def stream(self):
        """
            Yields Flow objects from the dump.
        """
        off = 0
        try:
            while 1:
                data = tnetstring.load(self.fo)
                if tuple(data["version"]) != version.IVERSION:
                    v = ".".join(str(i) for i in data["version"])
                    raise FlowReadError("Incompatible serialized data version: %s"%v)
                off = self.fo.tell()
                yield Flow._from_state(data)
        except ValueError, v:
            # Error is due to EOF
            if self.fo.tell() == off and self.fo.read() == '':
                return
            raise FlowReadError("Invalid data format.")


class FilteredFlowWriter:
    def __init__(self, fo, filt):
        self.fo = fo
        self.filt = filt

    def add(self, f):
        if self.filt and not f.match(self.filt):
            return
        d = f._get_state()
        tnetstring.dump(d, self.fo)


