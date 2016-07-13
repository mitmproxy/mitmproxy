from __future__ import absolute_import, print_function, division

from mitmproxy.builtins import anticomp
from mitmproxy.builtins import stickyauth


def default_addons():
    return [
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
    ]
