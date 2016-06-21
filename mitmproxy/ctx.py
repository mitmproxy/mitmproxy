from __future__ import absolute_import, print_function, division

from mitmproxy import ctxmanager

_flow = None
_log = None
_master = None


flow = ctxmanager.Facade(lambda: _flow)
log = ctxmanager.Facade(lambda: _log)
master = ctxmanager.Facade(lambda: _master)
