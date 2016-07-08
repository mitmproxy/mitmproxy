from __future__ import absolute_import, print_function, division

import collections
import hashlib
import re

from six.moves import http_cookiejar
from six.moves import urllib

from mitmproxy import controller
from mitmproxy import filt
from netlib import wsgi
from netlib import version
from netlib import strutils
from netlib.http import cookies
from netlib.http import http1


class AppRegistry:
    def __init__(self):
        self.apps = {}

    def add(self, app, domain, port):
        """
            Add a WSGI app to the registry, to be served for requests to the
            specified domain, on the specified port.
        """
        self.apps[(domain, port)] = wsgi.WSGIAdaptor(
            app,
            domain,
            port,
            version.MITMPROXY
        )

    def get(self, request):
        """
            Returns an WSGIAdaptor instance if request matches an app, or None.
        """
        if (request.host, request.port) in self.apps:
            return self.apps[(request.host, request.port)]
        if "host" in request.headers:
            host = request.headers["host"]
            return self.apps.get((host, request.port), None)


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
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s)
            tuples.
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
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s)
            tuples.
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
                    f.response.headers.pop(header, None)
                else:
                    f.request.headers.pop(header, None)
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    f.response.headers.add(header, value)
                else:
                    f.request.headers.add(header, value)


class StreamLargeBodies(object):
    def __init__(self, max_size):
        self.max_size = max_size

    def run(self, flow, is_request):
        r = flow.request if is_request else flow.response
        expected_size = http1.expected_http_body_size(
            flow.request, flow.response if not is_request else None
        )
        if not r.content and not (0 <= expected_size <= self.max_size):
            # r.stream may already be a callable, which we want to preserve.
            r.stream = r.stream or True


class ClientPlaybackState:
    def __init__(self, flows, exit):
        self.flows, self.exit = flows, exit
        self.current = None
        self.testing = False  # Disables actual replay for testing.

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

    def tick(self, master):
        if self.flows and not self.current:
            self.current = self.flows.pop(0).copy()
            if not self.testing:
                master.replay_request(self.current)
            else:
                self.current.reply = controller.DummyReply()
                master.request(self.current)
                if self.current.response:
                    master.response(self.current)


class ServerPlaybackState:
    def __init__(
            self,
            headers,
            flows,
            exit,
            nopop,
            ignore_params,
            ignore_content,
            ignore_payload_params,
            ignore_host):
        """
            headers: Case-insensitive list of request headers that should be
            included in request-response matching.
        """
        self.headers = headers
        self.exit = exit
        self.nopop = nopop
        self.ignore_params = ignore_params
        self.ignore_content = ignore_content
        self.ignore_payload_params = [strutils.always_bytes(x) for x in (ignore_payload_params or ())]
        self.ignore_host = ignore_host
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

        _, _, path, _, query, _ = urllib.parse.urlparse(r.url)
        queriesArray = urllib.parse.parse_qsl(query, keep_blank_values=True)

        key = [
            str(r.port),
            str(r.scheme),
            str(r.method),
            str(path),
        ]

        if not self.ignore_content:
            form_contents = r.urlencoded_form or r.multipart_form
            if self.ignore_payload_params and form_contents:
                key.extend(
                    p for p in form_contents.items(multi=True)
                    if p[0] not in self.ignore_payload_params
                )
            else:
                key.append(str(r.content))

        if not self.ignore_host:
            key.append(r.host)

        filtered = []
        ignore_params = self.ignore_params or []
        for p in queriesArray:
            if p[0] not in ignore_params:
                filtered.append(p)
        for p in filtered:
            key.append(p[0])
            key.append(p[1])

        if self.headers:
            headers = []
            for i in self.headers:
                v = r.headers.get(i)
                headers.append((i, v))
            key.append(headers)
        return hashlib.sha256(repr(key).encode("utf8", "surrogateescape")).digest()

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
        self.jar = collections.defaultdict(dict)
        self.flt = flt

    def ckey(self, attrs, f):
        """
            Returns a (domain, port, path) tuple.
        """
        domain = f.request.host
        path = "/"
        if "domain" in attrs:
            domain = attrs["domain"]
        if "path" in attrs:
            path = attrs["path"]
        return (domain, f.request.port, path)

    def domain_match(self, a, b):
        if http_cookiejar.domain_match(a, b):
            return True
        elif http_cookiejar.domain_match(a, b.strip(".")):
            return True
        return False

    def handle_response(self, f):
        for name, (value, attrs) in f.response.cookies.items(multi=True):
            # FIXME: We now know that Cookie.py screws up some cookies with
            # valid RFC 822/1123 datetime specifications for expiry. Sigh.
            a = self.ckey(attrs, f)
            if self.domain_match(f.request.host, a[0]):
                b = attrs.with_insert(0, name, value)
                self.jar[a][name] = b

    def handle_request(self, f):
        l = []
        if f.match(self.flt):
            for domain, port, path in self.jar.keys():
                match = [
                    self.domain_match(f.request.host, domain),
                    f.request.port == port,
                    f.request.path.startswith(path)
                ]
                if all(match):
                    c = self.jar[(domain, port, path)]
                    l.extend([cookies.format_cookie_header(c[name].items(multi=True)) for name in c.keys()])
        if l:
            f.request.stickycookie = True
            f.request.headers["cookie"] = "; ".join(l)


class StickyAuthState:
    def __init__(self, flt):
        """
            flt: Compiled filter.
        """
        self.flt = flt
        self.hosts = {}

    def handle_request(self, f):
        host = f.request.host
        if "authorization" in f.request.headers:
            self.hosts[host] = f.request.headers["authorization"]
        elif f.match(self.flt):
            if host in self.hosts:
                f.request.headers["authorization"] = self.hosts[host]
