from pathod import pathoc_cmdline as cmdline
import tutils
from six.moves import cStringIO as StringIO
import mock


@mock.patch("argparse.ArgumentParser.error")
def test_pathoc(perror):
    assert cmdline.args_pathoc(["pathoc", "foo.com", "get:/"])
    s = StringIO()
    with tutils.raises(SystemExit):
        cmdline.args_pathoc(["pathoc", "--show-uas"], s, s)

    a = cmdline.args_pathoc(["pathoc", "foo.com:8888", "get:/"])
    assert a.port == 8888

    a = cmdline.args_pathoc(["pathoc", "foo.com:xxx", "get:/"])
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathoc(["pathoc", "-I", "10, 20", "foo.com:8888", "get:/"])
    assert a.ignorecodes == [10, 20]

    a = cmdline.args_pathoc(["pathoc", "-I", "xx, 20", "foo.com:8888", "get:/"])
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathoc(["pathoc", "-c", "foo:10", "foo.com:8888", "get:/"])
    assert a.connect_to == ["foo", 10]

    a = cmdline.args_pathoc(["pathoc", "foo.com", "get:/", "--http2"])
    assert a.use_http2 == True
    assert a.ssl == True

    a = cmdline.args_pathoc(["pathoc", "foo.com", "get:/", "--http2-skip-connection-preface"])
    assert a.use_http2 == True
    assert a.ssl == True
    assert a.http2_skip_connection_preface == True

    a = cmdline.args_pathoc(["pathoc", "-c", "foo", "foo.com:8888", "get:/"])
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathoc(
        ["pathoc", "-c", "foo:bar", "foo.com:8888", "get:/"])
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathoc(
        [
            "pathoc",
            "foo.com:8888",
            tutils.test_data.path("data/request")
        ]
    )
    assert len(list(a.requests)) == 1

    with tutils.raises(SystemExit):
        cmdline.args_pathoc(["pathoc", "foo.com", "invalid"], s, s)
