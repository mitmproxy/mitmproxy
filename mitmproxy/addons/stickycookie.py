import collections
from http import cookiejar

from mitmproxy.net.http import cookies

from mitmproxy import exceptions
from mitmproxy import flowfilter


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
    if cookiejar.domain_match(a, b):
        return True
    elif cookiejar.domain_match(a, b.strip(".")):
        return True
    return False


class StickyCookie:
    def __init__(self):
        self.jar = collections.defaultdict(dict)
        self.flt = None

    def configure(self, options, updated):
        if "stickycookie" in updated:
            if options.stickycookie:
                flt = flowfilter.parse(options.stickycookie)
                if not flt:
                    raise exceptions.OptionsError(
                        "stickycookie: invalid filter expression: %s" % options.stickycookie
                    )
                self.flt = flt
            else:
                self.flt = None

    def response(self, flow):
        if self.flt:
            for name, (value, attrs) in flow.response.cookies.items(multi=True):
                # FIXME: We now know that Cookie.py screws up some cookies with
                # valid RFC 822/1123 datetime specifications for expiry. Sigh.
                dom_port_path = ckey(attrs, flow)

                if domain_match(flow.request.host, dom_port_path[0]):
                    if cookies.is_expired(attrs):
                        # Remove the cookie from jar
                        self.jar[dom_port_path].pop(name, None)

                        # If all cookies of a dom_port_path have been removed
                        # then remove it from the jar itself
                        if not self.jar[dom_port_path]:
                            self.jar.pop(dom_port_path, None)
                    else:
                        b = attrs.copy()
                        b.insert(0, name, value)
                        self.jar[dom_port_path][name] = b

    def request(self, flow):
        if self.flt:
            l = []
            if flowfilter.match(self.flt, flow):
                for domain, port, path in self.jar.keys():
                    match = [
                        domain_match(flow.request.host, domain),
                        flow.request.port == port,
                        flow.request.path.startswith(path)
                    ]
                    if all(match):
                        c = self.jar[(domain, port, path)]
                        l.extend([cookies.format_cookie_header(c[name].items(multi=True)) for name in c.keys()])
            if l:
                # FIXME: we need to formalise this...
                flow.request.stickycookie = True
                flow.request.headers["cookie"] = "; ".join(l)
