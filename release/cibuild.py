#!/usr/bin/env python3

import contextlib
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import click
import cryptography.fernet
import parver


@contextlib.contextmanager
def chdir(path: Path):  # pragma: no cover
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


class BuildError(Exception):
    pass


def bool_from_env(envvar: str) -> bool:
    val = os.environ.get(envvar, "")
    if not val or val.lower() in ("0", "false"):
        return False
    else:
        return True


class ZipFile2(zipfile.ZipFile):
    # ZipFile and tarfile have slightly different APIs. Let's fix that.
    def add(self, name: str, arcname: str) -> None:
        return self.write(name, arcname)

    def __enter__(self) -> "ZipFile2":
        return self


@dataclass(frozen=True, repr=False)
class BuildEnviron:
    PLATFORM_TAGS = {
        "Darwin": "osx",
        "Windows": "windows",
        "Linux": "linux",
    }

    system: str
    root_dir: Path
    branch: Optional[str] = None
    tag: Optional[str] = None
    is_pull_request: bool = True
    should_build_wheel: bool = False
    should_build_docker: bool = False
    should_build_pyinstaller: bool = False
    should_build_wininstaller: bool = False
    has_aws_creds: bool = False
    has_twine_creds: bool = False
    docker_username: Optional[str] = None
    docker_password: Optional[str] = None
    build_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "BuildEnviron":
        branch = None
        tag = None

        if ref := os.environ.get("GITHUB_REF", ""):
            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")
            if ref.startswith("refs/pull/"):
                branch = "pr-" + ref.split("/")[2]
            if ref.startswith("refs/tags/"):
                tag = ref.replace("refs/tags/", "")

        is_pull_request = os.environ.get("GITHUB_EVENT_NAME", "pull_request") == "pull_request"

        return cls(
            system=platform.system(),
            root_dir=Path(__file__).parent.parent,
            branch=branch,
            tag=tag,
            is_pull_request=is_pull_request,
            should_build_wheel=bool_from_env("CI_BUILD_WHEEL"),
            should_build_pyinstaller=bool_from_env("CI_BUILD_PYINSTALLER"),
            should_build_wininstaller=bool_from_env("CI_BUILD_WININSTALLER"),
            should_build_docker=bool_from_env("CI_BUILD_DOCKER"),
            has_aws_creds=bool_from_env("AWS_ACCESS_KEY_ID"),
            has_twine_creds=bool_from_env("TWINE_USERNAME") and bool_from_env("TWINE_PASSWORD"),
            docker_username=os.environ.get("DOCKER_USERNAME", None),
            docker_password=os.environ.get("DOCKER_PASSWORD", None),
            build_key=os.environ.get("CI_BUILD_KEY", None),
        )

    def archive(self, path: Path) -> Union[tarfile.TarFile, ZipFile2]:
        if self.system == "Windows":
            return ZipFile2(path, "w")
        else:
            return tarfile.open(path, "w:gz")

    @property
    def archive_path(self) -> Path:
        if self.system == "Windows":
            ext = "zip"
        else:
            ext = "tar.gz"
        return self.dist_dir / f"mitmproxy-{self.version}-{self.platform_tag}.{ext}"

    @property
    def build_dir(self) -> Path:
        return self.release_dir / "build"

    @property
    def dist_dir(self) -> Path:
        return self.release_dir / "dist"

    @property
    def docker_tag(self) -> str:
        if self.branch == "main":
            t = "dev"
        else:
            t = self.version
        return f"mitmproxy/mitmproxy:{t}"

    def dump_info(self, fp=sys.stdout) -> None:
        lst = [
            "version",
            "tag",
            "branch",
            "platform_tag",
            "root_dir",
            "release_dir",
            "build_dir",
            "dist_dir",
            "upload_dir",
            "should_build_wheel",
            "should_build_pyinstaller",
            "should_build_wininstaller",
            "should_build_docker",
            "should_upload_aws",
            "should_upload_docker",
            "should_upload_pypi",
        ]
        for attr in lst:
            print(f"cibuild.{attr}={getattr(self, attr)}", file=fp)

    def check_version(self) -> None:
        """
        Check that version numbers match our conventions.
        Raises a ValueError if there is a mismatch.
        """
        contents = (self.root_dir / "mitmproxy" / "version.py").read_text("utf8")
        match = re.search(r'^VERSION = "(.+?)"', contents, re.M)
        assert match
        version = match.group(1)

        if self.is_prod_release:
            # For production releases, we require strict version equality
            if self.version != version:
                raise ValueError(f"Tag is {self.tag}, but mitmproxy/version.py is {version}.")
        elif not self.is_maintenance_branch:
            # Commits on maintenance branches don't need the dev suffix. This
            # allows us to incorporate and test commits between tagged releases.
            # For snapshots, we only ensure that mitmproxy/version.py contains a
            # dev release.
            version_info = parver.Version.parse(version)
            if not version_info.is_devrelease:
                raise ValueError(f"Non-production releases must have dev suffix: {version}")

    @property
    def is_maintenance_branch(self) -> bool:
        """
            Is this an untagged commit on a maintenance branch?
        """
        if not self.tag and self.branch and re.match(r"v\d+\.x", self.branch):
            return True
        return False

    @property
    def has_docker_creds(self) -> bool:
        return bool(self.docker_username and self.docker_password)

    @property
    def is_prod_release(self) -> bool:
        if not self.tag or not self.tag.startswith("v"):
            return False
        try:
            v = parver.Version.parse(self.version, strict=True)
        except (parver.ParseError, BuildError):
            return False
        return not v.is_prerelease

    @property
    def platform_tag(self) -> str:
        if self.system in self.PLATFORM_TAGS:
            return self.PLATFORM_TAGS[self.system]
        raise BuildError(f"Unsupported platform: {self.system}")

    @property
    def release_dir(self) -> Path:
        return self.root_dir / "release"

    @property
    def should_upload_docker(self) -> bool:
        return all([
            (self.is_prod_release or self.branch in ["main", "dockertest"]),
            self.should_build_docker,
            self.has_docker_creds,
        ])

    @property
    def should_upload_aws(self) -> bool:
        return all([
            self.has_aws_creds,
            (self.should_build_wheel or self.should_build_pyinstaller or self.should_build_wininstaller),
        ])

    @property
    def should_upload_pypi(self) -> bool:
        return all([
            self.is_prod_release,
            self.should_build_wheel,
            self.has_twine_creds,
        ])

    @property
    def upload_dir(self) -> str:
        if self.tag:
            return self.version
        else:
            return f"branches/{self.version}"

    @property
    def version(self) -> str:
        if self.tag:
            if self.tag.startswith("v"):
                try:
                    parver.Version.parse(self.tag[1:], strict=True)
                except parver.ParseError:
                    return self.tag
                return self.tag[1:]
            return self.tag
        elif self.branch:
            return self.branch
        else:
            raise BuildError("We're on neither a tag nor a branch - could not establish version")


def build_wheel(be: BuildEnviron) -> None:  # pragma: no cover
    click.echo("Building wheel...")
    subprocess.check_call([
        "python",
        "setup.py",
        "-q",
        "bdist_wheel",
        "--dist-dir", be.dist_dir,
    ])
    whl, = be.dist_dir.glob('mitmproxy-*-py3-none-any.whl')
    click.echo(f"Found wheel package: {whl}")
    subprocess.check_call(["tox", "-e", "wheeltest", "--", whl])


DOCKER_PLATFORMS = "linux/amd64,linux/arm64"


def build_docker_image(be: BuildEnviron) -> None:  # pragma: no cover
    click.echo("Building Docker images...")

    whl, = be.dist_dir.glob('mitmproxy-*-py3-none-any.whl')
    docker_build_dir = be.release_dir / "docker"
    shutil.copy(whl, docker_build_dir / whl.name)

    subprocess.check_call([
        "docker", "buildx", "build",
        "--tag", be.docker_tag,
        "--platform", DOCKER_PLATFORMS,
        "--build-arg", f"MITMPROXY_WHEEL={whl.name}",
        "."
    ], cwd=docker_build_dir)
    # smoke-test the newly built docker image

    # build again without --platform but with --load to make the tag available,
    # see https://github.com/docker/buildx/issues/59#issuecomment-616050491
    subprocess.check_call([
        "docker", "buildx", "build",
        "--tag", be.docker_tag,
        "--load",
        "--build-arg", f"MITMPROXY_WHEEL={whl.name}",
        "."
    ], cwd=docker_build_dir)
    r = subprocess.run([
        "docker",
        "run",
        "--rm",
        be.docker_tag,
        "mitmdump",
        "--version",
    ], check=True, capture_output=True)
    print(r.stdout.decode())
    assert "Mitmproxy: " in r.stdout.decode()


def build_pyinstaller(be: BuildEnviron) -> None:  # pragma: no cover
    click.echo("Building pyinstaller package...")

    PYINSTALLER_SPEC = be.release_dir / "specs"
    PYINSTALLER_HOOKS = be.release_dir / "hooks"
    PYINSTALLER_TEMP = be.build_dir / "pyinstaller"
    PYINSTALLER_DIST = be.build_dir / "binaries" / be.platform_tag

    if PYINSTALLER_TEMP.exists():
        shutil.rmtree(PYINSTALLER_TEMP)
    if PYINSTALLER_DIST.exists():
        shutil.rmtree(PYINSTALLER_DIST)

    if be.platform_tag == "windows":
        with chdir(PYINSTALLER_SPEC):
            click.echo("Building PyInstaller binaries in directory mode...")
            subprocess.check_call(
                [
                    "pyinstaller",
                    "--clean",
                    "--workpath", PYINSTALLER_TEMP,
                    "--distpath", PYINSTALLER_DIST,
                    "./windows-dir.spec"
                ]
            )
            for tool in ["mitmproxy", "mitmdump", "mitmweb"]:
                click.echo(f"> {tool} --version")
                executable = (PYINSTALLER_DIST / "onedir" / tool).with_suffix(".exe")
                click.echo(subprocess.check_output([executable, "--version"]).decode())

    with be.archive(be.archive_path) as archive:
        for tool in ["mitmproxy", "mitmdump", "mitmweb"]:
            # We can't have a folder and a file with the same name.
            if tool == "mitmproxy":
                tool = "mitmproxy_main"
            # Make sure that we are in the spec folder.
            with chdir(PYINSTALLER_SPEC):
                click.echo(f"Building PyInstaller {tool} binary...")
                excludes = []
                if tool != "mitmweb":
                    excludes.append("mitmproxy.tools.web")
                if tool != "mitmproxy_main":
                    excludes.append("mitmproxy.tools.console")

                subprocess.check_call(
                    [   # type: ignore
                        "pyinstaller",
                        "--clean",
                        "--workpath", PYINSTALLER_TEMP,
                        "--distpath", PYINSTALLER_DIST,
                        "--additional-hooks-dir", PYINSTALLER_HOOKS,
                        "--onefile",
                        "--console",
                        "--icon", "icon.ico",
                    ]
                    + [x for e in excludes for x in ["--exclude-module", e]]
                    + [tool]
                )
                # Delete the spec file - we're good without.
                os.remove(f"{tool}.spec")

            executable = PYINSTALLER_DIST / tool
            if be.platform_tag == "windows":
                executable = executable.with_suffix(".exe")

            # Remove _main suffix from mitmproxy executable
            if "_main" in executable.name:
                executable = executable.rename(
                    executable.with_name(executable.name.replace("_main", ""))
                )

            # Test if it works at all O:-)
            click.echo(f"> {executable} --version")
            click.echo(subprocess.check_output([executable, "--version"]).decode())

            archive.add(str(executable), str(executable.name))
    click.echo("Packed {}.".format(be.archive_path.name))


def build_wininstaller(be: BuildEnviron) -> None:  # pragma: no cover
    click.echo("Building wininstaller package...")

    IB_VERSION = "21.6.0"
    IB_SETUP_SHA256 = "2bc9f9945cb727ad176aa31fa2fa5a8c57a975bad879c169b93e312af9d05814"
    IB_DIR = be.release_dir / "installbuilder"
    IB_SETUP = IB_DIR / "setup" / f"{IB_VERSION}-installer.exe"
    IB_CLI = Path(fr"C:\Program Files\VMware InstallBuilder Enterprise {IB_VERSION}\bin\builder-cli.exe")
    IB_LICENSE = IB_DIR / "license.xml"

    if not IB_LICENSE.exists() and not be.build_key:
        click.echo("Cannot build windows installer without secret key.")
        return

    if not IB_CLI.exists():
        if not IB_SETUP.exists():
            click.echo("Downloading InstallBuilder...")

            def report(block, blocksize, total):
                done = block * blocksize
                if round(100 * done / total) != round(100 * (done - blocksize) / total):
                    click.secho(f"Downloading... {round(100 * done / total)}%")

            tmp = IB_SETUP.with_suffix(".tmp")
            urllib.request.urlretrieve(
                f"https://clients.bitrock.com/installbuilder/installbuilder-enterprise-{IB_VERSION}-windows-x64-installer.exe",
                tmp,
                reporthook=report
            )
            tmp.rename(IB_SETUP)

        ib_setup_hash = hashlib.sha256()
        with IB_SETUP.open("rb") as fp:
            while True:
                data = fp.read(65_536)
                if not data:
                    break
                ib_setup_hash.update(data)
        if ib_setup_hash.hexdigest() != IB_SETUP_SHA256:  # pragma: no cover
            raise RuntimeError("InstallBuilder hashes don't match.")

        click.echo("Install InstallBuilder...")
        subprocess.run([IB_SETUP, "--mode", "unattended", "--unattendedmodeui", "none"], check=True)
        assert IB_CLI.is_file()

    if not IB_LICENSE.exists():
        assert be.build_key
        click.echo("Decrypt InstallBuilder license...")
        f = cryptography.fernet.Fernet(be.build_key.encode())
        with open(IB_LICENSE.with_suffix(".xml.enc"), "rb") as infile, \
                open(IB_LICENSE, "wb") as outfile:
            outfile.write(f.decrypt(infile.read()))

    click.echo("Run InstallBuilder...")
    subprocess.run([
        IB_CLI,
        "build",
        str(IB_DIR / "mitmproxy.xml"),
        "windows",
        "--license", str(IB_LICENSE),
        "--setvars", f"project.version={be.version}",
        "--verbose"
    ], check=True)
    assert (be.dist_dir / f"mitmproxy-{be.version}-windows-installer.exe").exists()


@click.group(chain=True)
def cli():  # pragma: no cover
    """
    mitmproxy build tool
    """
    pass


@cli.command("build")
def build():  # pragma: no cover
    """
        Build a binary distribution
    """
    be = BuildEnviron.from_env()
    be.dump_info()

    be.check_version()
    os.makedirs(be.dist_dir, exist_ok=True)

    if be.should_build_wheel:
        build_wheel(be)
    if be.should_build_docker:
        build_docker_image(be)
    if be.should_build_pyinstaller:
        build_pyinstaller(be)
    if be.should_build_wininstaller:
        build_wininstaller(be)


@cli.command("upload")
def upload():  # pragma: no cover
    """
        Upload build artifacts

        Uploads the wheels package to PyPi.
        Uploads the Pyinstaller and wheels packages to the snapshot server.
        Pushes the Docker image to Docker Hub.
    """
    be = BuildEnviron.from_env()
    be.dump_info()

    if be.is_pull_request:
        click.echo("Refusing to upload artifacts from a pull request!")
        return

    if be.should_upload_aws:
        num_files = len([name for name in be.dist_dir.iterdir() if name.is_file()])
        click.echo(f"Uploading {num_files} files to AWS dir {be.upload_dir}...")
        subprocess.check_call([
            "aws", "s3", "cp",
            "--acl", "public-read",
            f"{be.dist_dir}/",
            f"s3://snapshots.mitmproxy.org/{be.upload_dir}/",
            "--recursive",
        ])

    if be.should_upload_pypi:
        whl, = be.dist_dir.glob('mitmproxy-*-py3-none-any.whl')
        click.echo(f"Uploading {whl} to PyPi...")
        subprocess.check_call(["twine", "upload", whl])

    if be.should_upload_docker:
        click.echo(f"Uploading Docker image to tag={be.docker_tag}...")
        subprocess.check_call([
            "docker",
            "login",
            "-u", be.docker_username,
            "-p", be.docker_password,
        ])

        whl, = be.dist_dir.glob('mitmproxy-*-py3-none-any.whl')
        docker_build_dir = be.release_dir / "docker"
        shutil.copy(whl, docker_build_dir / whl.name)
        # buildx is a bit weird in that we need to reinvoke build, but oh well.
        subprocess.check_call([
            "docker", "buildx", "build",
            "--tag", be.docker_tag,
            "--push",
            "--platform", DOCKER_PLATFORMS,
            "--build-arg", f"MITMPROXY_WHEEL={whl.name}",
            "."
        ], cwd=docker_build_dir)

        if be.is_prod_release:
            subprocess.check_call([
                "docker", "buildx", "build",
                "--tag", "mitmproxy/mitmproxy:latest",
                "--push",
                "--platform", DOCKER_PLATFORMS,
                "--build-arg", f"MITMPROXY_WHEEL={whl.name}",
                "."
            ], cwd=docker_build_dir)


if __name__ == "__main__":  # pragma: no cover
    cli()
