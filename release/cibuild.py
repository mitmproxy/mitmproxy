#!/usr/bin/env python3

import contextlib
import glob
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

import click
import cryptography.fernet
import parver


@contextlib.contextmanager
def chdir(path: str):  # pragma: no cover
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


class BuildError(Exception):
    pass


class BuildEnviron:
    PLATFORM_TAGS = {
        "Darwin": "osx",
        "Windows": "windows",
        "Linux": "linux",
    }

    def __init__(
        self,
        *,
        system="",
        root_dir="",
        travis_tag="",
        travis_branch="",
        travis_pull_request="",
        appveyor_repo_tag_name="",
        appveyor_repo_branch="",
        appveyor_pull_request_number="",
        should_build_wheel=False,
        should_build_docker=False,
        should_build_pyinstaller=False,
        should_build_wininstaller=False,
        has_aws_creds=False,
        has_twine_creds=False,
        docker_username="",
        docker_password="",
        rtool_key="",
    ):
        self.system = system
        self.root_dir = root_dir

        self.travis_tag = travis_tag
        self.travis_branch = travis_branch
        self.travis_pull_request = travis_pull_request

        self.should_build_wheel = should_build_wheel
        self.should_build_docker = should_build_docker
        self.should_build_pyinstaller = should_build_pyinstaller
        self.should_build_wininstaller = should_build_wininstaller

        self.appveyor_repo_tag_name = appveyor_repo_tag_name
        self.appveyor_repo_branch = appveyor_repo_branch
        self.appveyor_pull_request_number = appveyor_pull_request_number

        self.has_aws_creds = has_aws_creds
        self.has_twine_creds = has_twine_creds
        self.docker_username = docker_username
        self.docker_password = docker_password
        self.rtool_key = rtool_key

    @classmethod
    def from_env(cls):
        return cls(
            system=platform.system(),
            root_dir=os.path.normpath(os.path.join(os.path.dirname(__file__), "..")),
            travis_tag=os.environ.get("TRAVIS_TAG", ""),
            travis_branch=os.environ.get("TRAVIS_BRANCH", ""),
            travis_pull_request=os.environ.get("TRAVIS_PULL_REQUEST"),
            appveyor_repo_tag_name=os.environ.get("APPVEYOR_REPO_TAG_NAME", ""),
            appveyor_repo_branch=os.environ.get("APPVEYOR_REPO_BRANCH", ""),
            appveyor_pull_request_number=os.environ.get("APPVEYOR_PULL_REQUEST_NUMBER"),
            should_build_wheel="WHEEL" in os.environ,
            should_build_pyinstaller="PYINSTALLER" in os.environ,
            should_build_wininstaller="WININSTALLER" in os.environ,
            should_build_docker="DOCKER" in os.environ,
            has_aws_creds="AWS_ACCESS_KEY_ID" in os.environ,
            has_twine_creds=(
                "TWINE_USERNAME" in os.environ and
                "TWINE_PASSWORD" in os.environ
            ),
            docker_username=os.environ.get("DOCKER_USERNAME"),
            docker_password=os.environ.get("DOCKER_PASSWORD"),
            rtool_key=os.environ.get("RTOOL_KEY"),
        )

    def archive(self, path):
        # ZipFile and tarfile have slightly different APIs. Fix that.
        if self.system == "Windows":
            a = zipfile.ZipFile(path, "w")
            a.add = a.write
            return a
        else:
            return tarfile.open(path, "w:gz")

    def archive_name(self, bdist: str) -> str:
        if self.system == "Windows":
            ext = "zip"
        else:
            ext = "tar.gz"
        return "{project}-{version}-{platform}.{ext}".format(
            project=bdist,
            version=self.version,
            platform=self.platform_tag,
            ext=ext
        )

    @property
    def bdists(self):
        ret = {
            "mitmproxy": ["mitmproxy", "mitmdump", "mitmweb"],
            "pathod": ["pathoc", "pathod"]
        }
        if self.system == "Windows":
            ret["mitmproxy"].remove("mitmproxy")
        return ret

    @property
    def branch(self):
        return self.travis_branch or self.appveyor_repo_branch

    @property
    def build_dir(self):
        return os.path.join(self.release_dir, "build")

    @property
    def dist_dir(self):
        return os.path.join(self.release_dir, "dist")

    @property
    def docker_tag(self):
        if self.branch == "master":
            t = "dev"
        else:
            t = self.version
        return "mitmproxy/mitmproxy:{}".format(t)

    def dump_info(self, fp=sys.stdout):
        lst = [
            "version",
            "tag",
            "branch",
            "platform_tag",
            "root_dir",
            "release_dir",
            "build_dir",
            "dist_dir",
            "bdists",
            "upload_dir",
            "should_build_wheel",
            "should_build_pyinstaller",
            "should_build_docker",
            "should_upload_docker",
            "should_upload_pypi",
        ]
        for attr in lst:
            print(f"cibuild.{attr}={getattr(self, attr)}", file=fp)

    @property
    def has_docker_creds(self) -> bool:
        return bool(self.docker_username and self.docker_password)

    @property
    def is_prod_release(self) -> bool:
        if not self.tag:
            return False
        try:
            v = parver.Version.parse(self.version, strict=True)
        except (parver.ParseError, BuildError):
            return False
        return not v.is_prerelease

    @property
    def is_pull_request(self) -> bool:
        if self.appveyor_pull_request_number:
            return True
        if self.travis_pull_request and self.travis_pull_request != "false":
            return True
        return False

    @property
    def platform_tag(self):
        if self.system in self.PLATFORM_TAGS:
            return self.PLATFORM_TAGS[self.system]
        raise BuildError("Unsupported platform: %s" % self.system)

    @property
    def release_dir(self):
        return os.path.join(self.root_dir, "release")

    @property
    def should_upload_docker(self) -> bool:
        return all([
            (self.is_prod_release or self.branch == "master"),
            self.should_build_docker,
            self.has_docker_creds,
        ])

    @property
    def should_upload_pypi(self) -> bool:
        return all([
            self.is_prod_release,
            self.should_build_wheel,
            self.has_twine_creds,
        ])

    @property
    def tag(self):
        return self.travis_tag or self.appveyor_repo_tag_name

    @property
    def upload_dir(self):
        if self.tag:
            return self.version
        else:
            return "branches/%s" % self.version

    @property
    def version(self):
        name = self.tag or self.branch
        if not name:
            raise BuildError("We're on neither a tag nor a branch - could not establish version")
        return name


def build_wheel(be: BuildEnviron):  # pragma: no cover
    click.echo("Building wheel...")
    subprocess.check_call([
        "python",
        "setup.py",
        "-q",
        "bdist_wheel",
        "--dist-dir", be.dist_dir,
    ])
    whl = glob.glob(os.path.join(be.dist_dir, 'mitmproxy-*-py3-none-any.whl'))[0]
    click.echo("Found wheel package: {}".format(whl))
    subprocess.check_call(["tox", "-e", "wheeltest", "--", whl])
    return whl


def build_docker_image(be: BuildEnviron, whl: str):  # pragma: no cover
    click.echo("Building Docker image...")
    subprocess.check_call([
        "docker",
        "build",
        "--tag", be.docker_tag,
        "--build-arg", "WHEEL_MITMPROXY={}".format(whl),
        "--build-arg", "WHEEL_BASENAME_MITMPROXY={}".format(os.path.basename(whl)),
        "--file", "docker/Dockerfile",
        "."
    ])


def build_pyinstaller(be: BuildEnviron):  # pragma: no cover
    click.echo("Building pyinstaller package...")

    PYINSTALLER_SPEC = os.path.join(be.release_dir, "specs")
    # PyInstaller 3.2 does not bundle pydivert's Windivert binaries
    PYINSTALLER_HOOKS = os.path.abspath(os.path.join(be.release_dir, "hooks"))
    PYINSTALLER_TEMP = os.path.abspath(os.path.join(be.build_dir, "pyinstaller"))
    PYINSTALLER_DIST = os.path.abspath(os.path.join(be.build_dir, "binaries", be.platform_tag))

    # https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
    # scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
    if platform.system() == "Windows":
        PYINSTALLER_ARGS = [
            # PyInstaller < 3.2 does not handle Python 3.5's ucrt correctly.
            "-p", r"C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x86",
        ]
    else:
        PYINSTALLER_ARGS = []

    if os.path.exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if os.path.exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    for bdist, tools in sorted(be.bdists.items()):
        with be.archive(os.path.join(be.dist_dir, be.archive_name(bdist))) as archive:
            for tool in tools:
                # We can't have a folder and a file with the same name.
                if tool == "mitmproxy":
                    tool = "mitmproxy_main"
                # This is PyInstaller, so it messes up paths.
                # We need to make sure that we are in the spec folder.
                with chdir(PYINSTALLER_SPEC):
                    click.echo("Building PyInstaller %s binary..." % tool)
                    excludes = []
                    if tool != "mitmweb":
                        excludes.append("mitmproxy.tools.web")
                    if tool != "mitmproxy_main":
                        excludes.append("mitmproxy.tools.console")

                    subprocess.check_call(
                        [
                            "pyinstaller",
                            "--clean",
                            "--workpath", PYINSTALLER_TEMP,
                            "--distpath", PYINSTALLER_DIST,
                            "--additional-hooks-dir", PYINSTALLER_HOOKS,
                            "--onefile",
                            "--console",
                            "--icon", "icon.ico",
                            # This is PyInstaller, so setting a
                            # different log level obviously breaks it :-)
                            # "--log-level", "WARN",
                        ]
                        + [x for e in excludes for x in ["--exclude-module", e]]
                        + PYINSTALLER_ARGS
                        + [tool]
                    )
                    # Delete the spec file - we're good without.
                    os.remove("{}.spec".format(tool))

                # Test if it works at all O:-)
                executable = os.path.join(PYINSTALLER_DIST, tool)
                if platform.system() == "Windows":
                    executable += ".exe"

                # Remove _main suffix from mitmproxy executable
                if "_main" in executable:
                    shutil.move(
                        executable,
                        executable.replace("_main", "")
                    )
                    executable = executable.replace("_main", "")

                click.echo("> %s --version" % executable)
                click.echo(subprocess.check_output([executable, "--version"]).decode())

                archive.add(executable, os.path.basename(executable))
        click.echo("Packed {}.".format(be.archive_name(bdist)))


def build_wininstaller(be: BuildEnviron):  # pragma: no cover
    click.echo("Building wininstaller package...")

    IB_VERSION = "18.5.2"
    IB_DIR = pathlib.Path(be.release_dir) / "installbuilder"
    IB_SETUP = IB_DIR / "setup" / f"{IB_VERSION}-installer.exe"
    IB_CLI = fr"C:\Program Files (x86)\BitRock InstallBuilder Enterprise {IB_VERSION}\bin\builder-cli.exe"
    IB_LICENSE = IB_DIR / "license.xml"

    if True or not os.path.isfile(IB_CLI):
        if not os.path.isfile(IB_SETUP):
            click.echo("Downloading InstallBuilder...")

            def report(block, blocksize, total):
                done = block * blocksize
                if round(100 * done / total) != round(100 * (done - blocksize) / total):
                    click.secho(f"Downloading... {round(100*done/total)}%")

            urllib.request.urlretrieve(
                f"https://installbuilder.bitrock.com/installbuilder-enterprise-{IB_VERSION}-windows-installer.exe",
                IB_SETUP.with_suffix(".tmp"),
                reporthook=report
            )
            shutil.move(IB_SETUP.with_suffix(".tmp"), IB_SETUP)

        click.echo("Install InstallBuilder...")
        subprocess.run([str(IB_SETUP), "--mode", "unattended", "--unattendedmodeui", "none"],
                       check=True)
        assert os.path.isfile(IB_CLI)

    click.echo("Decrypt InstallBuilder license...")
    f = cryptography.fernet.Fernet(be.rtool_key.encode())
    with open(IB_LICENSE.with_suffix(".xml.enc"), "rb") as infile, open(IB_LICENSE,
                                                                        "wb") as outfile:
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
    assert os.path.isfile(
        os.path.join(be.dist_dir, f"mitmproxy-{be.version}-windows-installer.exe"))


@contextlib.contextmanager
def set_version(be: BuildEnviron) -> None:  # pragma: no cover
    VERSION_FILE = pathlib.Path(be.root_dir) / "mitmproxy" / "version.py"

    if be.tag:
        # this must not fail.
        parver.Version.parse(be.version, strict=True)

        with open(VERSION_FILE, "r") as f:
            existing_version = f.read()

        new_version = re.sub(
            r'^VERSION = ".+?"', f'VERSION = "{be.version}"',
            existing_version,
            flags=re.M
        )

        with open(VERSION_FILE, "w") as f:
            f.write(new_version)
        try:
            yield
        finally:
            with open(VERSION_FILE, "w") as f:
                f.write(existing_version)
    else:
        yield


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

    os.makedirs(be.dist_dir, exist_ok=True)

    with set_version(be):
        if be.should_build_wheel:
            whl = build_wheel(be)
            # Docker image requires wheels
            if be.should_build_docker:
                build_docker_image(be, whl)
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

    if be.is_pull_request:
        click.echo("Refusing to upload artifacts from a pull request!")
        return

    if be.has_aws_creds:
        subprocess.check_call([
            "aws", "s3", "cp",
            "--acl", "public-read",
            be.dist_dir + "/",
            "s3://snapshots.mitmproxy.org/{}/".format(be.upload_dir),
            "--recursive",
        ])

    if be.should_upload_pypi:
        whl = glob.glob(os.path.join(be.dist_dir, 'mitmproxy-*-py3-none-any.whl'))[0]
        click.echo("Uploading {} to PyPi...".format(whl))
        subprocess.check_call(["twine", "upload", whl])

    if be.should_upload_docker:
        click.echo("Uploading Docker image to tag={}...".format(be.docker_tag))
        subprocess.check_call([
            "docker",
            "login",
            "-u", be.docker_username,
            "-p", be.docker_password,
        ])
        subprocess.check_call(["docker", "push", be.docker_tag])


if __name__ == "__main__":  # pragma: no cover
    cli()
