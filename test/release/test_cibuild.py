import io
import os

import pytest

from release import cibuild


def test_buildenviron_live():
    be = cibuild.BuildEnviron.from_env()
    assert be.release_dir


def test_buildenviron_common():
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir="/foo",
        travis_branch="master",
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
        system="Unknown",
        root_dir="/foo",
    )
    with pytest.raises(cibuild.BuildError):
        be.version
    with pytest.raises(cibuild.BuildError):
        be.platform_tag

    with pytest.raises(ValueError, match="TRAVIS_TAG"):
        be = cibuild.BuildEnviron(
            system="Linux",
            root_dir="/foo",
            travis_tag="one",
            travis_branch="two",
        )


def test_buildenviron_pr():
    # Simulates a PR. We build everything, but don't have access to secret
    # credential env variables.
    be = cibuild.BuildEnviron(
        travis_tag="",
        travis_branch="master",
        travis_pull_request="true",
        should_build_wheel=True,
        should_build_pyinstaller=True,
        should_build_docker=True,
    )
    assert be.is_pull_request

    # Mini test for appveyor
    be = cibuild.BuildEnviron(
        appveyor_pull_request_number="xxxx",
    )
    assert be.is_pull_request
    assert not be.is_prod_release
    assert not be.is_maintenance_branch


def test_buildenviron_commit():
    # Simulates an ordinary commit on the master branch.
    be = cibuild.BuildEnviron(
        travis_tag="",
        travis_branch="master",
        travis_pull_request="false",
        should_build_wheel=True,
        should_build_pyinstaller=True,
        should_build_docker=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.docker_tag == "mitmproxy/mitmproxy:dev"
    assert be.should_upload_docker
    assert not be.should_upload_pypi
    assert be.should_upload_docker
    assert not be.is_prod_release
    assert not be.is_maintenance_branch


def test_buildenviron_releasetag():
    # Simulates a tagged release on a release branch.
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir="/foo",
        travis_tag="v0.0.1",
        travis_branch="v0.0.1",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == "v0.0.1"
    assert be.branch == "v0.0.1"
    assert be.version == "0.0.1"
    assert be.upload_dir == "0.0.1"
    assert be.docker_tag == "mitmproxy/mitmproxy:0.0.1"
    assert be.should_upload_pypi
    assert be.should_upload_docker
    assert be.is_prod_release
    assert not be.is_maintenance_branch


def test_buildenviron_namedtag():
    # Simulates a non-release tag on a branch.
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir="/foo",
        travis_tag="anyname",
        travis_branch="anyname",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == "anyname"
    assert be.branch == "anyname"
    assert be.version == "anyname"
    assert be.upload_dir == "anyname"
    assert be.docker_tag == "mitmproxy/mitmproxy:anyname"
    assert not be.should_upload_pypi
    assert not be.should_upload_docker
    assert not be.is_prod_release
    assert not be.is_maintenance_branch


def test_buildenviron_dev_branch():
    # Simulates a commit on a development branch on the main repo
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir="/foo",
        travis_tag="",
        travis_branch="mybranch",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == ""
    assert be.branch == "mybranch"
    assert be.version == "mybranch"
    assert be.upload_dir == "branches/mybranch"
    assert not be.should_upload_pypi
    assert not be.should_upload_docker
    assert not be.is_maintenance_branch


def test_buildenviron_maintenance_branch():
    # Simulates a commit on a release maintenance branch on the main repo
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir="/foo",
        travis_tag="",
        travis_branch="v0.x",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == ""
    assert be.branch == "v0.x"
    assert be.version == "v0.x"
    assert be.upload_dir == "branches/v0.x"
    assert not be.should_upload_pypi
    assert not be.should_upload_docker
    assert be.is_maintenance_branch


def test_buildenviron_osx(tmpdir):
    be = cibuild.BuildEnviron(
        system="Darwin",
        root_dir="/foo",
        travis_tag="0.0.1",
        travis_branch="0.0.1",
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
        system="Windows",
        root_dir="/foo",
        travis_tag="v0.0.1",
        travis_branch="v0.0.1",
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


@pytest.mark.parametrize("version, tag, ok", [
    ("3.0.0.dev", "", True),  # regular snapshot
    ("3.0.0.dev", "v3.0.0", False),  # forgot to remove ".dev" on bump
    ("3.0.0", "", False),  # forgot to re-add ".dev"
    ("3.0.0", "v4.0.0", False),  # version mismatch
    ("3.0.0", "v3.0.0", True),  # regular release
    ("3.0.0.rc1", "v3.0.0.rc1", False),  # non-canonical.
    ("3.0.0.dev", "anyname", True),  # tagged test/dev release
    ("3.0.0", "3.0.0", False),  # tagged, but without v prefix
])
def test_buildenviron_check_version(version, tag, ok, tmpdir):
    tmpdir.mkdir("mitmproxy").join("version.py").write(f'VERSION = "{version}"')

    be = cibuild.BuildEnviron(
        root_dir=tmpdir,
        travis_tag=tag,
        travis_branch=tag or "branch",
    )
    if ok:
        be.check_version()
    else:
        with pytest.raises(ValueError):
            be.check_version()
