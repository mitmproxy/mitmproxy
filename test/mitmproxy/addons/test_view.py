import pytest

from mitmproxy.test import tflow

from mitmproxy.addons import view, viewhttp1, viewhttp2
from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import io
from mitmproxy.test import taddons
from mitmproxy.tools.console import consoleaddons


def tft(*, method="get", start=0):
    f = tflow.tflow()
    f.request.method = method
    f.request.timestamp_start = start
    return f



def test_orders():
    for v in (viewhttp1.ViewHttp1(), viewhttp2.ViewHttp2()):
        with taddons.context(v):
            assert v.order_options()


def test_setgetval():
    for v in (viewhttp1.ViewHttp1(), viewhttp2.ViewHttp2()):
        with taddons.context():
            f = tflow.tflow()
            v.add([f])
            v.setvalue([f], "key", "value")
            assert v.getvalue(f, "key", "default") == "value"
            assert v.getvalue(f, "unknow", "default") == "default"

            v.setvalue_toggle([f], "key")
            assert v.getvalue(f, "key", "default") == "true"
            v.setvalue_toggle([f], "key")
            assert v.getvalue(f, "key", "default") == "false"
