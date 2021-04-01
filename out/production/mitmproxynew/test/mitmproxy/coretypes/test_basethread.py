import re
from mitmproxy.coretypes import basethread


def test_basethread():
    t = basethread.BaseThread('foobar')
    assert re.match(r'foobar - age: \d+s', t._threadinfo())
