import os
import io
from release import cibuild


def test_buildenviron_common():
    be = cibuild.BuildEnviron(
        system = "Linux",
        root_dir = "/foo",

        travis_tag = "v0.0.1",
        travis_branch = "v0.x",
    )
    assert be.release_dir == os.path.join(be.root_dir, "release")
    assert be.dist_dir == os.path.join(be.root_dir, "release", "dist")
    assert be.build_dir == os.path.join(be.root_dir, "release", "build")
    assert be.is_pull_request is False

    cs = io.StringIO()
    be.dump_info(cs)
    assert cs.getvalue()


def test_buildenviron_pr():
    be = cibuild.BuildEnviron(
        travis_tag = "v0.0.1",
        travis_branch = "v0.x",
        travis_pull_request = "true",
    )
    assert be.is_pull_request

    be = cibuild.BuildEnviron(
        appveyor_pull_request_number = "xxxx",
    )
    assert be.is_pull_request


def test_buildenviron_tag():
    be = cibuild.BuildEnviron(
        system = "Linux",
        root_dir = "/foo",

        travis_tag = "v0.0.1",
        travis_branch = "v0.x",
    )
    assert be.tag == "v0.0.1"
    assert be.branch == "v0.x"
    assert be.version == "0.0.1"
    assert be.upload_dir == "0.0.1"


def test_buildenviron_branch():
    be = cibuild.BuildEnviron(
        system = "Linux",
        root_dir = "/foo",

        travis_tag = "",
        travis_branch = "v0.x",
    )
    assert be.tag == ""
    assert be.branch == "v0.x"
    assert be.version == "0.x"
    assert be.upload_dir == "branches/0.x"


def test_buildenviron_osx():
    be = cibuild.BuildEnviron(
        system = "Darwin",
        root_dir = "/foo",

        travis_tag = "v0.0.1",
        travis_branch = "v0.x",
    )
    assert be.platform_tag == "osx"
    assert be.bdists == {
        "mitmproxy": ["mitmproxy", "mitmdump", "mitmweb"],
        "pathod": ["pathoc", "pathod"],
    }
    assert be.archive_name("mitmproxy") == "mitmproxy-0.0.1-osx.tar.gz"


def test_buildenviron_windows():
    be = cibuild.BuildEnviron(
        system = "Windows",
        root_dir = "/foo",

        travis_tag = "v0.0.1",
        travis_branch = "v0.x",
    )
    assert be.platform_tag == "windows"
    assert be.bdists == {
        "mitmproxy": ["mitmdump", "mitmweb"],
        "pathod": ["pathoc", "pathod"],
    }
    assert be.archive_name("mitmproxy") == "mitmproxy-0.0.1-windows.zip"