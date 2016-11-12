import binascii

import passlib.apache

from mitmproxy import exceptions


def parse_http_basic_auth(s):
    words = s.split()
    if len(words) != 2:
        return None
    scheme = words[0]
    try:
        user = binascii.a2b_base64(words[1]).decode("utf8", "replace")
    except binascii.Error:
        return None
    parts = user.split(':')
    if len(parts) != 2:
        return None
    return scheme, parts[0], parts[1]


def assemble_http_basic_auth(scheme, username, password):
    v = binascii.b2a_base64(
        (username + ":" + password).encode("utf8")
    ).decode("ascii")
    return scheme + " " + v


class ProxyAuth:
    def __init__(self):
        self.nonanonymous = False
        self.htpasswd = None
        self.singleuser = None

    def configure(self, options, updated):
        if "auth_nonanonymous" in updated:
            self.nonanonymous = options.auth_nonanonymous
        if "auth_singleuser" in updated:
            if options.auth_singleuser:
                parts = options.auth_singleuser.split(':')
                if len(parts) != 2:
                    raise exceptions.OptionsError(
                        "Invalid single-user auth specification."
                    )
                self.singleuser = parts
            else:
                self.singleuser = None
        if "auth_htpasswd" in updated:
            if options.auth_htpasswd:
                try:
                    self.htpasswd = passlib.apache.HtpasswdFile(
                        options.auth_htpasswd
                    )
                except (ValueError, OSError) as v:
                    raise exceptions.OptionsError(
                        "Could not open htpasswd file: %s" % v
                    )
            else:
                self.auth_htpasswd = None

    def http_connect(self, f):
        # mode = regular
        pass

    def http_request(self, f):
        # mode = regular, no via
        pass
