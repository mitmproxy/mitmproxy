import re
from mitmproxy.types import basethread


def test_basethread():
    t = basethread.BaseThread('foobar')
    assert re.match('foobar - age: \d+s', t._threadinfo())
