from mitmproxy.addons.comment import Comment
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_comment():
    c = Comment()
    f = tflow.tflow()

    with taddons.context():
        c.comment([f], "foo")

    assert f.comment == "foo"
