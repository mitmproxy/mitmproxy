from mitmproxy.test import tflow, taddons
from mitmproxy.addons.comment import Comment


def test_comment():
    c = Comment()
    f = tflow.tflow()

    with taddons.context():
        c.comment([f], "foo")

    assert f.comment == "foo"
