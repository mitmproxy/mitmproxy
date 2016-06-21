import collections
from six.moves import http_cookiejar
from netlib.http import cookies

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import filt


def ckey(attrs, f):
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


def domain_match(a, b):
    if http_cookiejar.domain_match(a, b):
        return True
    elif http_cookiejar.domain_match(a, b.strip(".")):
        return True
    return False


class StickyCookie:
    def __init__(self):
        self.jar = collections.defaultdict(dict)
        self.flt = None

    def configure(self, options):
        if options.stickycookie:
            flt = filt.parse(options.stickycookie)
            if not flt:
                raise exceptions.OptionsError(
                    "stickycookie: invalid filter expression: %s" % options.stickycookie
                )
            self.flt = flt

    def response(self):
        if self.flt:
            for name, (value, attrs) in ctx.flow.response.cookies.items(multi=True):
                # FIXME: We now know that Cookie.py screws up some cookies with
                # valid RFC 822/1123 datetime specifications for expiry. Sigh.
                a = ckey(attrs, ctx.flow)
                if domain_match(ctx.flow.request.host, a[0]):
                    b = attrs.with_insert(0, name, value)
                    self.jar[a][name] = b

    def request(self):
        if self.flt:
            l = []
            if ctx.flow.match(self.flt):
                for domain, port, path in self.jar.keys():
                    match = [
                        domain_match(ctx.flow.request.host, domain),
                        ctx.flow.request.port == port,
                        ctx.flow.request.path.startswith(path)
                    ]
                    if all(match):
                        c = self.jar[(domain, port, path)]
                        l.extend([cookies.format_cookie_header(c[name].items(multi=True)) for name in c.keys()])
            if l:
                # FIXME: we need to formalise this...
                ctx.flow.request.stickycookie = True
                ctx.flow.request.headers["cookie"] = "; ".join(l)
