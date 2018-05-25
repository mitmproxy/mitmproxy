import os
import io

import pytest

from release import cibuild


def test_buildenviron_live():
    be = cibuild.BuildEnviron.from_env()
    assert be.release_dir


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
    assert not be.has_docker_creds

    cs = io.StringIO()
    be.dump_info(cs)
    assert cs.getvalue()

    be = cibuild.BuildEnviron(
        system = "Unknown",
        root_dir = "/foo",
    )
    with pytest.raises(cibuild.BuildError):
        be.version
    with pytest.raises(cibuild.BuildError):
        be.platform_tag


def test_buildenviron_pr():
    # Simulates a PR. We build everything, but don't have access to secret
    # credential env variables.
    be = cibuild.BuildEnviron(
        travis_tag = "",
        travis_branch = "master",
        travis_pull_request = "true",

        should_build_wheel = True,
        should_build_pyinstaller = True,
        should_build_docker = True,
    )
    assert be.is_pull_request

    # Mini test for appveyor
    be = cibuild.BuildEnviron(
        appveyor_pull_request_number = "xxxx",
    )
    assert be.is_pull_request
    assert not be.is_prod_release


def test_buildenviron_commit():
    # Simulates an ordinary commit on the master branch.
    be = cibuild.BuildEnviron(
        travis_tag = "",
        travis_branch = "master",
        travis_pull_request = "false",

        should_build_wheel = True,
        should_build_pyinstaller = True,
        should_build_docker = True,
        docker_username = "foo",
        docker_password = "bar",
    )
    assert be.docker_tag == "mitmproxy/mitmproxy:dev"
    assert be.should_upload_docker
    assert not be.should_upload_pypi
    assert be.should_upload_docker
    assert not be.is_prod_release


def test_buildenviron_rleasetag():
    # Simulates a tagged release on a release branch.
    be = cibuild.BuildEnviron(
        system = "Linux",
        root_dir = "/foo",

        travis_tag = "v0.0.1",
        travis_branch = "v0.x",

        should_build_wheel = True,
        should_build_docker = True,
        should_build_pyinstaller = True,
        has_twine_creds = True,
        docker_username = "foo",
        docker_password = "bar",
    )
    assert be.tag == "v0.0.1"
    assert be.branch == "v0.x"
    assert be.version == "0.0.1"
    assert be.upload_dir == "0.0.1"
    assert be.docker_tag == "mitmproxy/mitmproxy:0.0.1"
    assert be.should_upload_pypi
    assert be.should_upload_docker
    assert be.is_prod_release


def test_buildenviron_branch():
    # Simulates a development branch on the main repo
    be = cibuild.BuildEnviron(
        system = "Linux",
        root_dir = "/foo",

        travis_tag = "",
        travis_branch = "mybranch",

        should_build_wheel = True,
        should_build_docker = True,
        should_build_pyinstaller = True,
        has_twine_creds = True,
        docker_username = "foo",
        docker_password = "bar",
    )
    assert be.tag == ""
    assert be.branch == "mybranch"
    assert be.version == "mybranch"
    assert be.upload_dir == "branches/mybranch"
    assert not be.should_upload_pypi
    assert not be.should_upload_docker


def test_buildenviron_osx(tmpdir):
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

    a = be.archive(os.path.join(tmpdir, "arch"))
    assert a
    a.close()


def test_buildenviron_windows(tmpdir):
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

    a = be.archive(os.path.join(tmpdir, "arch"))
    assert a
    a.close()