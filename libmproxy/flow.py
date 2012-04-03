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
import hashlib, Cookie, cookielib, copy, re, urlparse
import time
import tnetstring, filt, script, utils, encoding, proxy
from email.utils import parsedate_tz, formatdate, mktime_tz
import controller, version, certutils

HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"


class ReplaceHooks:
    def __init__(self):
        self.lst = []

    def add(self, fpatt, rex, s):
        """
            Add a replacement hook.

            fpatt: A string specifying a filter pattern.
            rex: A regular expression.
            s: The replacement string

            Returns True if hook was added, False if the pattern could not be
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

    def remove(self, fpatt, rex, s):
        """
            Remove a hook.

            patt: A string specifying a filter pattern.
            func: Optional callable. If not specified, all hooks matching patt are removed.
        """
        for i in range(len(self.lst)-1, -1, -1):
            if (fpatt, rex, s) == self.lst[i][:3]:
                del self.lst[i]

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


class ODict:
    """
        A dictionary-like object for managing ordered (key, value) data.
    """
    def __init__(self, lst=None):
        self.lst = lst or []

    def _kconv(self, s):
        return s

    def __eq__(self, other):
        return self.lst == other.lst

    def __getitem__(self, k):
        """
            Returns a list of values matching key.
        """
        ret = []
        k = self._kconv(k)
        for i in self.lst:
            if self._kconv(i[0]) == k:
                ret.append(i[1])
        return ret

    def _filter_lst(self, k, lst):
        new = []
        for i in lst:
            if self._kconv(i[0]) != k:
                new.append(i)
        return new

    def __len__(self):
        """
            Total number of (key, value) pairs.
        """
        return len(self.lst)

    def __setitem__(self, k, valuelist):
        """
            Sets the values for key k. If there are existing values for this
            key, they are cleared.
        """
        if isinstance(valuelist, basestring):
            raise ValueError("ODict valuelist should be lists.")
        k = self._kconv(k)
        new = self._filter_lst(k, self.lst)
        for i in valuelist:
            new.append((k, i))
        self.lst = new

    def __delitem__(self, k):
        """
            Delete all items matching k.
        """
        self.lst = self._filter_lst(k, self.lst)

    def __contains__(self, k):
        for i in self.lst:
            if self._kconv(i[0]) == k:
                return True
        return False

    def add(self, key, value):
        self.lst.append([key, str(value)])

    def get(self, k, d=None):
        if k in self:
            return self[k]
        else:
            return d

    def _get_state(self):
        return [tuple(i) for i in self.lst]

    @classmethod
    def _from_state(klass, state):
        return klass([list(i) for i in state])

    def copy(self):
        """
            Returns a copy of this object.
        """
        lst = copy.deepcopy(self.lst)
        return self.__class__(lst)

    def __repr__(self):
        elements = []
        for itm in self.lst:
            elements.append(itm[0] + ": " + itm[1])
        elements.append("")
        return "\r\n".join(elements)

    def in_any(self, key, value, caseless=False):
        """
            Do any of the values matching key contain value?

            If caseless is true, value comparison is case-insensitive.
        """
        if caseless:
            value = value.lower()
        for i in self[key]:
            if caseless:
                i = i.lower()
            if value in i:
                return True
        return False

    def match_re(self, expr):
        """
            Match the regular expression against each (key, value) pair. For
            each pair a string of the following format is matched against:

            "key: value"
        """
        for k, v in self.lst:
            s = "%s: %s"%(k, v)
            if re.search(expr, s):
                return True
        return False

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both keys and
            values. Encoded content will be decoded before replacement, and
            re-encoded afterwards.

            Returns the number of replacements made.
        """
        nlst, count = [], 0
        for i in self.lst:
            k, c = re.subn(pattern, repl, i[0], *args, **kwargs)
            count += c
            v, c = re.subn(pattern, repl, i[1], *args, **kwargs)
            count += c
            nlst.append([k, v])
        self.lst = nlst
        return count


class ODictCaseless(ODict):
    """
        A variant of ODict with "caseless" keys. This version _preserves_ key
        case, but does not consider case when setting or getting items.
    """
    def _kconv(self, s):
        return s.lower()


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
        ce = o.headers["content-encoding"]
        if ce and ce[0] in encoding.ENCODINGS:
            self.ce = ce[0]
        else:
            self.ce = None

    def __enter__(self):
        if self.ce:
            self.o.decode()

    def __exit__(self, type, value, tb):
        if self.ce:
            self.o.encode(self.ce)


class HTTPMsg(controller.Msg):
    def decode(self):
        """
            Decodes content based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.
        """
        ce = self.headers["content-encoding"]
        if not ce or ce[0] not in encoding.ENCODINGS:
            return
        self.content = encoding.decode(
            ce[0],
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


class Request(HTTPMsg):
    """
        An HTTP request.

        Exposes the following attributes:

            client_conn: ClientConnect object, or None if this is a replay.
            headers: ODictCaseless object
            content: Content of the request, or None

            scheme: URL scheme (http/https)
            host: Host portion of the URL
            port: Destination port
            path: Path portion of the URL

            timestamp: Seconds since the epoch
            method: HTTP method
    """
    def __init__(self, client_conn, host, port, scheme, method, path, headers, content, timestamp=None):
        assert isinstance(headers, ODictCaseless)
        self.client_conn = client_conn
        self.host, self.port, self.scheme = host, port, scheme
        self.method, self.path, self.headers, self.content = method, path, headers, content
        self.timestamp = timestamp or utils.timestamp()
        self.close = False
        controller.Msg.__init__(self)

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
        self.timestamp = state["timestamp"]

    def _get_state(self):
        return dict(
            client_conn = self.client_conn._get_state() if self.client_conn else None,
            host = self.host,
            port = self.port,
            scheme = self.scheme,
            method = self.method,
            path = self.path,
            headers = self.headers._get_state(),
            content = self.content,
            timestamp = self.timestamp,
        )

    @classmethod
    def _from_state(klass, state):
        return klass(
            ClientConnect._from_state(state["client_conn"]),
            str(state["host"]),
            state["port"],
            str(state["scheme"]),
            str(state["method"]),
            str(state["path"]),
            ODictCaseless._from_state(state["headers"]),
            state["content"],
            state["timestamp"]
        )

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self._get_state() == other._get_state()

    def copy(self):
        """
            Returns a copy of this object.
        """
        c = copy.copy(self)
        c.acked = True
        c.headers = self.headers.copy()
        return c

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.headers.in_any("content-type", HDR_FORM_URLENCODED, True):
            return ODict(utils.urldecode(self.content))
        return ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        self.headers["Content-Type"] = [HDR_FORM_URLENCODED]
        self.content = utils.urlencode(odict.lst)

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

    def get_url(self):
        """
            Returns a URL string, constructed from the Request's URL compnents.
        """
        return utils.unparse_url(self.scheme, self.host, self.port, self.path)

    def set_url(self, url):
        """
            Parses a URL specification, and updates the Request's information
            accordingly.

            Returns False if the URL was invalid, True if the request succeeded.
        """
        parts = utils.parse_url(url)
        if not parts:
            return False
        self.scheme, self.host, self.port, self.path = parts
        return True

    def _assemble(self, _proxy = False):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.
        """
        FMT = '%s %s HTTP/1.1\r\n%s\r\n%s'
        FMT_PROXY = '%s %s://%s:%s%s HTTP/1.1\r\n%s\r\n%s'

        headers = self.headers.copy()
        utils.del_all(
            headers,
            [
                'proxy-connection',
                'keep-alive',
                'connection',
                'content-length',
                'transfer-encoding'
            ]
        )
        if not 'host' in headers:
            headers["host"] = [utils.hostport(self.scheme, self.host, self.port)]
        content = self.content
        if content is None:
            content = ""
        else:
            headers["content-length"] = [str(len(content))]
        if self.close:
            headers["connection"] = ["close"]
        if not _proxy:
            return FMT % (self.method, self.path, str(headers), content)
        else:
            return FMT_PROXY % (self.method, self.scheme, self.host, self.port, self.path, str(headers), content)

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = re.subn(pattern, repl, self.content, *args, **kwargs)
        self.path, pc = re.subn(pattern, repl, self.path, *args, **kwargs)
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
            content: Response content
            timestamp: Seconds since the epoch
    """
    def __init__(self, request, code, msg, headers, content, der_cert, timestamp=None):
        assert isinstance(headers, ODictCaseless)
        self.request = request
        self.code, self.msg = code, msg
        self.headers, self.content = headers, content
        self.der_cert = der_cert
        self.timestamp = timestamp or utils.timestamp()
        controller.Msg.__init__(self)
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
        delta = now - self.timestamp
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
        self.timestamp = state["timestamp"]
        self.der_cert = state["der_cert"]

    def get_cert(self):
        """
            Returns a certutils.SSLCert object, or None.
        """
        if self.der_cert:
            return certutils.SSLCert.from_der(self.der_cert)

    def _get_state(self):
        return dict(
            code = self.code,
            msg = self.msg,
            headers = self.headers._get_state(),
            timestamp = self.timestamp,
            der_cert = self.der_cert,
            content = self.content
        )

    @classmethod
    def _from_state(klass, request, state):
        return klass(
            request,
            state["code"],
            str(state["msg"]),
            ODictCaseless._from_state(state["headers"]),
            state["content"],
            state.get("der_cert"),
            state["timestamp"],
        )

    def __eq__(self, other):
        return self._get_state() == other._get_state()

    def copy(self):
        """
            Returns a copy of this object.
        """
        c = copy.copy(self)
        c.acked = True
        c.headers = self.headers.copy()
        return c

    def _assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.
        """
        FMT = '%s\r\n%s\r\n%s'
        headers = self.headers.copy()
        utils.del_all(
            headers,
            ['proxy-connection', 'connection', 'keep-alive', 'transfer-encoding']
        )
        content = self.content
        if content is None:
            content = ""
        else:
            headers["content-length"] = [str(len(content))]
        if self.request.client_conn.close:
            headers["connection"] = ["close"]
        proto = "HTTP/1.1 %s %s"%(self.code, str(self.msg))
        data = (proto, str(headers), content)
        return FMT%data

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the response. Encoded content will be decoded
            before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = re.subn(pattern, repl, self.content, *args, **kwargs)
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c


class ClientDisconnect(controller.Msg):
    """
        A client disconnection event.

        Exposes the following attributes:

            client_conn: ClientConnect object.
    """
    def __init__(self, client_conn):
        controller.Msg.__init__(self)
        self.client_conn = client_conn


class ClientConnect(controller.Msg):
    """
        A single client connection. Each connection can result in multiple HTTP
        Requests.

        Exposes the following attributes:

            address: (address, port) tuple, or None if the connection is replayed.
            requestcount: Number of requests created by this client connection.
            close: Is the client connection closed?
            connection_error: Error string or None.
    """
    def __init__(self, address):
        """
            address is an (address, port) tuple, or None if this connection has
            been replayed from within mitmproxy.
        """
        self.address = address
        self.close = False
        self.requestcount = 0
        self.connection_error = None
        controller.Msg.__init__(self)

    def __eq__(self, other):
        return self._get_state() == other._get_state()

    def _load_state(self, state):
        self.close = True
        self.requestcount = state["requestcount"]

    def _get_state(self):
        return dict(
            address = list(self.address),
            requestcount = self.requestcount,
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
        """
            Returns a copy of this object.
        """
        c = copy.copy(self)
        c.acked = True
        return c


class Error(controller.Msg):
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
        controller.Msg.__init__(self)

    def _load_state(self, state):
        self.msg = state["msg"]
        self.timestamp = state["timestamp"]

    def copy(self):
        """
            Returns a copy of this object.
        """
        c = copy.copy(self)
        c.acked = True
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

    def __eq__(self, other):
        return self._get_state() == other._get_state()

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the request. Returns the number of replacements
            made.

            FIXME: Is replace useful on an Error object??
        """
        self.msg, c = re.subn(pattern, repl, self.msg, *args, **kwargs)
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
            n.request.client_conn = None
            self.current = master.handle_request(n.request)
            if not testing and not self.current.response:
                #begin nocover
                master.replay_request(self.current)
                #end nocover
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
        """
        if f:
            return f(self)
        return True

    def kill(self, master):
        """
            Kill this request.
        """
        self.error = Error(self.request, "Connection killed")
        if self.request and not self.request.acked:
            self.request._ack(None)
        elif self.response and not self.response.acked:
            self.response._ack(None)
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
            if not self.request.acked:
                self.request._ack()
            elif self.response and not self.response.acked:
                self.response._ack()
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
        if f.match(self._limit):
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
            flow.request._ack(response)
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

        if self.server_playback:
            if self.server_playback.exit and self.server_playback.count() == 0:
                self.shutdown()

        return controller.Master.tick(self, q)

    def duplicate_flow(self, f):
        return self.load_flow(f.copy())

    def load_flow(self, f):
        """
            Loads a flow, and returns a new flow object.
        """
        if f.request:
            fr = self.handle_request(f.request)
        if f.response:
            self.handle_response(f.response)
        if f.error:
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
                    f.request._ack()

    def process_new_response(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_response(f)

    def replay_request(self, f):
        """
            Returns None if successful, or error message if not.
        """
        #begin nocover
        if f.intercepting:
            return "Can't replay while intercepting..."
        if f.request:
            f.request._set_replay()
            if f.request.content:
                f.request.headers["content-length"] = [str(len(f.request.content))]
            f.response = None
            f.error = None
            self.process_new_request(f)
            rt = proxy.RequestReplayThread(
                    self.server.config,
                    f,
                    self.masterq,
                )
            rt.start()
        #end nocover

    def run_script_hook(self, name, *args, **kwargs):
        if self.script and not self.pause_scripts:
            ret = self.script.run(name, *args, **kwargs)
            if not ret[0] and ret[1]:
                e = "Script error:\n" + ret[1][1]
                self.add_event(e, "error")

    def handle_clientconnect(self, cc):
        self.run_script_hook("clientconnect", cc)
        self.add_event("Connect from: %s:%s"%cc.address)
        cc._ack()

    def handle_clientdisconnect(self, r):
        self.run_script_hook("clientdisconnect", r)
        s = "Disconnect from: %s:%s"%r.client_conn.address
        self.add_event(s)
        if r.client_conn.requestcount:
            s = "    -> handled %s requests"%r.client_conn.requestcount
            self.add_event(s)
        if r.client_conn.connection_error:
            self.add_event(
                "   -> error: %s"%r.client_conn.connection_error, "error"
            )
        r._ack()

    def handle_error(self, r):
        f = self.state.add_error(r)
        self.replacehooks.run(f)
        if f:
            self.run_script_hook("error", f)
        if self.client_playback:
            self.client_playback.clear(f)
        r._ack()
        return f

    def handle_request(self, r):
        f = self.state.add_request(r)
        self.replacehooks.run(f)
        self.run_script_hook("request", f)
        self.process_new_request(f)
        return f

    def handle_response(self, r):
        f = self.state.add_response(r)
        self.replacehooks.run(f)
        if f:
            self.run_script_hook("response", f)
        if self.client_playback:
            self.client_playback.clear(f)
        if not f:
            r._ack()
        if f:
            self.process_new_response(f)
        return f

    def shutdown(self):
        if self.script:
            self.load_script(None)
        controller.Master.shutdown(self)


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
                off = self.fo.tell()
                yield Flow._from_state(data)
        except ValueError:
            # Error is due to EOF
            if self.fo.tell() == off and self.fo.read() == '':
                return
            raise FlowReadError("Invalid data format.")

