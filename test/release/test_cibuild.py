import io
from pathlib import Path

import pytest

from release import cibuild

root = Path(__file__).parent.parent.parent


def test_buildenviron_live():
    be = cibuild.BuildEnviron.from_env()
    assert be.release_dir


def test_buildenviron_common():
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir=root,
        branch="main",
    )
    assert be.release_dir == be.root_dir / "release"
    assert be.dist_dir == be.root_dir / "release" / "dist"
    assert be.build_dir == be.root_dir / "release" / "build"
    assert not be.has_docker_creds

    cs = io.StringIO()
    be.dump_info(cs)
    assert cs.getvalue()

    be = cibuild.BuildEnviron(
        system="Unknown",
        root_dir=root,
    )
    with pytest.raises(cibuild.BuildError):
        be.version
    with pytest.raises(cibuild.BuildError):
        be.platform_tag


def test_buildenviron_pr(monkeypatch):
    # Simulates a PR. We build everything, but don't have access to secret
    # credential env variables.
    monkeypatch.setenv("GITHUB_REF", "refs/pull/42/merge")
    monkeypatch.setenv("CI_BUILD_WHEEL", "1")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")

    be = cibuild.BuildEnviron.from_env()
    assert be.branch == "pr-42"
    assert be.is_pull_request
    assert be.should_build_wheel
    assert not be.should_upload_pypi


def test_buildenviron_commit():
    # Simulates an ordinary commit on the master branch.
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir=root,
        branch="main",
        is_pull_request=False,
        should_build_wheel=True,
        should_build_pyinstaller=True,
        should_build_docker=True,
        docker_username="foo",
        docker_password="bar",
        has_aws_creds=True,
    )
    assert be.docker_tag == "mitmproxy/mitmproxy:dev"
    assert be.should_upload_docker
    assert not be.should_upload_pypi
    assert be.should_upload_docker
    assert be.should_upload_aws
    assert not be.is_prod_release
    assert not be.is_maintenance_branch


def test_buildenviron_releasetag():
    # Simulates a tagged release on a release branch.
    be = cibuild.BuildEnviron(
        system="Linux",
        root_dir=root,
        tag="v0.0.1",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == "v0.0.1"
    assert be.branch is None
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
        root_dir=root,
        tag="anyname",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag == "anyname"
    assert be.branch is None
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
        root_dir=root,
        branch="mybranch",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag is None
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
        root_dir=root,
        branch="v0.x",
        should_build_wheel=True,
        should_build_docker=True,
        should_build_pyinstaller=True,
        has_twine_creds=True,
        docker_username="foo",
        docker_password="bar",
    )
    assert be.tag is None
    assert be.branch == "v0.x"
    assert be.version == "v0.x"
    assert be.upload_dir == "branches/v0.x"
    assert not be.should_upload_pypi
    assert not be.should_upload_docker
    assert be.is_maintenance_branch


def test_buildenviron_osx(tmp_path):
    be = cibuild.BuildEnviron(
        system="Darwin",
        root_dir=root,
        tag="v0.0.1",
    )
    assert be.platform_tag == "osx"
    assert be.archive_path == be.dist_dir / "mitmproxy-0.0.1-osx.tar.gz"

    with be.archive(tmp_path / "arch"):
        pass
    assert (tmp_path / "arch").exists()


def test_buildenviron_windows(tmp_path):
    be = cibuild.BuildEnviron(
        system="Windows",
        root_dir=root,
        tag="v0.0.1",
    )
    assert be.platform_tag == "windows"
    assert be.archive_path == be.dist_dir / "mitmproxy-0.0.1-windows.zip"

    with be.archive(tmp_path / "arch"):
        pass
    assert (tmp_path / "arch").exists()


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
        system="Windows",
        tag=tag,
    )
    if ok:
        be.check_version()
    else:
        with pytest.raises(ValueError):
            be.check_version()


def test_bool_from_env(monkeypatch):
    monkeypatch.setenv("FOO", "1")
    assert cibuild.bool_from_env("FOO")

    monkeypatch.setenv("FOO", "0")
    assert not cibuild.bool_from_env("FOO")

    monkeypatch.setenv("FOO", "false")
    assert not cibuild.bool_from_env("FOO")

    monkeypatch.setenv("FOO", "")
    assert not cibuild.bool_from_env("FOO")

    monkeypatch.delenv("FOO")
    assert not cibuild.bool_from_env("FOO")
