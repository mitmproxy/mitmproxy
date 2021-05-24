from mitmproxy.test import tflow
from mitmproxy.addons.comment import Comment


def test_comment():
    c = Comment()
    f = tflow.tflow()
    c.comment([f], "foo")

    assert f.metadata["comment"] == "foo"
