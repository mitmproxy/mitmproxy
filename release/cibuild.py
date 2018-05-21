#!/usr/bin/env python3

import glob
import re
import contextlib
import os
import platform
import sys
import shutil
import subprocess
import tarfile
import zipfile
from os.path import join, abspath, dirname, exists, basename

import click
import cryptography.fernet

# ZipFile and tarfile have slightly different APIs. Fix that.
if platform.system() == "Windows":
    def Archive(name):
        a = zipfile.ZipFile(name, "w")
        a.add = a.write
        return a
else:
    def Archive(name):
        return tarfile.open(name, "w:gz")

PLATFORM_TAG = {
    "Darwin": "osx",
    "Windows": "windows",
    "Linux": "linux",
}.get(platform.system(), platform.system())

ROOT_DIR = abspath(join(dirname(__file__), ".."))
RELEASE_DIR = join(ROOT_DIR, "release")
BUILD_DIR = join(RELEASE_DIR, "build")
DIST_DIR = join(RELEASE_DIR, "dist")

BDISTS = {
    "mitmproxy": ["mitmproxy", "mitmdump", "mitmweb"],
    "pathod": ["pathoc", "pathod"]
}
if platform.system() == "Windows":
    BDISTS["mitmproxy"].remove("mitmproxy")

TOOLS = [
    tool
    for tools in sorted(BDISTS.values())
    for tool in tools
]

TAG = os.environ.get("TRAVIS_TAG", os.environ.get("APPVEYOR_REPO_TAG_NAME", None))
BRANCH = os.environ.get("TRAVIS_BRANCH", os.environ.get("APPVEYOR_REPO_BRANCH", None))
if TAG:
    VERSION = re.sub('^v', '', TAG)
    UPLOAD_DIR = VERSION
elif BRANCH:
    VERSION = re.sub('^v', '', BRANCH)
    UPLOAD_DIR = "branches/%s" % VERSION
else:
    print("Could not establish build name - exiting." % BRANCH)
    sys.exit(0)

print("BUILD PLATFORM_TAG=%s" % PLATFORM_TAG)
print("BUILD ROOT_DIR=%s" % ROOT_DIR)
print("BUILD RELEASE_DIR=%s" % RELEASE_DIR)
print("BUILD BUILD_DIR=%s" % BUILD_DIR)
print("BUILD DIST_DIR=%s" % DIST_DIR)
print("BUILD BDISTS=%s" % BDISTS)
print("BUILD TAG=%s" % TAG)
print("BUILD BRANCH=%s" % BRANCH)
print("BUILD VERSION=%s" % VERSION)
print("BUILD UPLOAD_DIR=%s" % UPLOAD_DIR)


def archive_name(bdist: str) -> str:
    if platform.system() == "Windows":
        ext = "zip"
    else:
        ext = "tar.gz"
    return "{project}-{version}-{platform}.{ext}".format(
        project=bdist,
        version=VERSION,
        platform=PLATFORM_TAG,
        ext=ext
    )


@contextlib.contextmanager
def chdir(path: str):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


@click.group(chain=True)
def cli():
    """
    mitmproxy build tool
    """
    pass


@cli.command("build")
def build():
    """
    Build a binary distribution
    """
    os.makedirs(DIST_DIR, exist_ok=True)

    if "WHEEL" in os.environ:
        whl = build_wheel()
    else:
        click.echo("Not building wheels.")

    if "WHEEL" in os.environ and "DOCKER" in os.environ:
        # Docker image requires wheels
        build_docker_image(whl)
    else:
        click.echo("Not building Docker image.")

    if "PYINSTALLER" in os.environ:
        build_pyinstaller()
    else:
        click.echo("Not building PyInstaller packages.")


def build_wheel():
    click.echo("Building wheel...")
    subprocess.check_call([
        "python",
        "setup.py",
        "-q",
        "bdist_wheel",
        "--dist-dir", DIST_DIR,
    ])

    whl = glob.glob(join(DIST_DIR, 'mitmproxy-*-py3-none-any.whl'))[0]
    click.echo("Found wheel package: {}".format(whl))

    subprocess.check_call([
        "tox",
        "-e", "wheeltest",
        "--",
        whl
    ])

    return whl


def build_docker_image(whl):
    click.echo("Building Docker image...")
    subprocess.check_call([
        "docker",
        "build",
        "--build-arg", "WHEEL_MITMPROXY={}".format(os.path.relpath(whl, ROOT_DIR)),
        "--build-arg", "WHEEL_BASENAME_MITMPROXY={}".format(basename(whl)),
        "--file", "docker/Dockerfile",
        "."
    ])


def build_pyinstaller():
    PYINSTALLER_SPEC = join(RELEASE_DIR, "specs")
    # PyInstaller 3.2 does not bundle pydivert's Windivert binaries
    PYINSTALLER_HOOKS = join(RELEASE_DIR, "hooks")
    PYINSTALLER_TEMP = join(BUILD_DIR, "pyinstaller")
    PYINSTALLER_DIST = join(BUILD_DIR, "binaries", PLATFORM_TAG)

    # https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
    # scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
    if platform.system() == "Windows":
        PYINSTALLER_ARGS = [
            # PyInstaller < 3.2 does not handle Python 3.5's ucrt correctly.
            "-p", r"C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x86",
        ]
    else:
        PYINSTALLER_ARGS = []

    if exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    for bdist, tools in sorted(BDISTS.items()):
        with Archive(join(DIST_DIR, archive_name(bdist))) as archive:
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
                executable = join(PYINSTALLER_DIST, tool)
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

                archive.add(executable, basename(executable))
        click.echo("Packed {}.".format(archive_name(bdist)))


@cli.command("upload")
def upload():
    """
        Upload build artifacts

        Uploads the wheels package to PyPi.
        Uploads the Pyinstaller and wheels packages to the snapshot server.
        Pushes the Docker image to Docker Hub.
    """

    # Our credentials are only available from within the main repository and not forks.
    # We need to prevent uploads from all BUT the branches in the main repository.
    # Pull requests and master-branches of forks are not allowed to upload.
    is_pull_request = (
        ("TRAVIS_PULL_REQUEST" in os.environ and os.environ["TRAVIS_PULL_REQUEST"] != "false") or
        "APPVEYOR_PULL_REQUEST_NUMBER" in os.environ
    )
    if is_pull_request:
        click.echo("Refusing to upload artifacts from a pull request!")
        return

    if "AWS_ACCESS_KEY_ID" in os.environ:
        subprocess.check_call([
            "aws", "s3", "cp",
            "--acl", "public-read",
            DIST_DIR + "/",
            "s3://snapshots.mitmproxy.org/{}/".format(UPLOAD_DIR),
            "--recursive",
        ])

    upload_pypi = (
        TAG and
        "WHEEL" in os.environ and
        "TWINE_USERNAME" in os.environ and
        "TWINE_PASSWORD" in os.environ
    )
    if upload_pypi:
        whl = glob.glob(join(DIST_DIR, 'mitmproxy-*-py3-none-any.whl'))[0]
        click.echo("Uploading {} to PyPi...".format(whl))
        subprocess.check_call([
            "twine",
            "upload",
            whl
        ])

    upload_docker = (
        (TAG or BRANCH == "master") and
        "DOCKER" in os.environ and
        "DOCKER_USERNAME" in os.environ and
        "DOCKER_PASSWORD" in os.environ
    )
    if upload_docker:
        docker_tag = "dev" if BRANCH == "master" else VERSION

        click.echo("Uploading Docker image to tag={}...".format(docker_tag))
        subprocess.check_call([
            "docker",
            "login",
            "-u", os.environ["DOCKER_USERNAME"],
            "-p", os.environ["DOCKER_PASSWORD"],
        ])
        subprocess.check_call([
            "docker",
            "push",
            "mitmproxy/mitmproxy:{}".format(docker_tag),
        ])


@cli.command("decrypt")
@click.argument('infile', type=click.File('rb'))
@click.argument('outfile', type=click.File('wb'))
@click.argument('key', envvar='RTOOL_KEY')
def decrypt(infile, outfile, key):
    f = cryptography.fernet.Fernet(key.encode())
    outfile.write(f.decrypt(infile.read()))


if __name__ == "__main__":
    cli()
