from __future__ import (absolute_import, print_function, division)
import binascii
import collections
import string
import sys
import urlparse

from .. import utils

class Response(object):

    def __init__(
        self,
        httpversion,
        status_code,
        msg,
        headers,
        content,
        sslinfo=None,
    ):
        self.httpversion = httpversion
        self.status_code = status_code
        self.msg = msg
        self.headers = headers
        self.content = content
        self.sslinfo = sslinfo

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "Response(%s - %s)" % (self.status_code, self.msg)



def is_valid_port(port):
    if not 0 <= port <= 65535:
        return False
    return True


def is_valid_host(host):
    try:
        host.decode("idna")
    except ValueError:
        return False
    if "\0" in host:
        return None
    return True


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.

        Checks that:
            port is an integer 0-65535
            host is a valid IDNA-encoded hostname with no null-bytes
            path is valid ASCII
    """
    try:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    except ValueError:
        return None
    if not scheme:
        return None
    if '@' in netloc:
        # FIXME: Consider what to do with the discarded credentials here Most
        # probably we should extend the signature to return these as a separate
        # value.
        _, netloc = string.rsplit(netloc, '@', maxsplit=1)
    if ':' in netloc:
        host, port = string.rsplit(netloc, ':', maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    if not is_valid_host(host):
        return None
    if not utils.isascii(path):
        return None
    if not is_valid_port(port):
        return None
    return scheme, host, port, path


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    toks = []
    for i in headers[key]:
        for j in i.split(","):
            toks.append(j.strip())
    return toks
