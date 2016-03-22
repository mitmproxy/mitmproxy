from pathod import pathod_cmdline as cmdline
import tutils
import mock


@mock.patch("argparse.ArgumentParser.error")
def test_pathod(perror):
    assert cmdline.args_pathod(["pathod"])

    a = cmdline.args_pathod(
        [
            "pathod",
            "--cert",
            tutils.test_data.path("data/testkey.pem")
        ]
    )
    assert a.ssl_certs

    a = cmdline.args_pathod(
        [
            "pathod",
            "--cert",
            "nonexistent"
        ]
    )
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathod(
        [
            "pathod",
            "-a",
            "foo=200"
        ]
    )
    assert a.anchors

    a = cmdline.args_pathod(
        [
            "pathod",
            "-a",
            "foo=" + tutils.test_data.path("data/response")
        ]
    )
    assert a.anchors

    a = cmdline.args_pathod(
        [
            "pathod",
            "-a",
            "?=200"
        ]
    )
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathod(
        [
            "pathod",
            "-a",
            "foo"
        ]
    )
    assert perror.called
    perror.reset_mock()

    a = cmdline.args_pathod(
        [
            "pathod",
            "--limit-size",
            "200k"
        ]
    )
    assert a.sizelimit

    a = cmdline.args_pathod(
        [
            "pathod",
            "--limit-size",
            "q"
        ]
    )
    assert perror.called
    perror.reset_mock()
