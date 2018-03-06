#!/usr/bin/env python3

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

# https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
# scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
if platform.system() == "Windows":
    VENV_BIN = "Scripts"
    PYINSTALLER_ARGS = [
        # PyInstaller < 3.2 does not handle Python 3.5's ucrt correctly.
        "-p", r"C:\Program Files (x86)\Windows Kits\10\Redist\ucrt\DLLs\x86",
    ]
else:
    VENV_BIN = "bin"
    PYINSTALLER_ARGS = []

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

PYINSTALLER_SPEC = join(RELEASE_DIR, "specs")
# PyInstaller 3.2 does not bundle pydivert's Windivert binaries
PYINSTALLER_HOOKS = join(RELEASE_DIR, "hooks")
PYINSTALLER_TEMP = join(BUILD_DIR, "pyinstaller")
PYINSTALLER_DIST = join(BUILD_DIR, "binaries", PLATFORM_TAG)

VENV_DIR = join(BUILD_DIR, "venv")

# Project Configuration
SNAPSHOT_BRANCHES = ["master", "updocs"]
VERSION_FILE = join(ROOT_DIR, "mitmproxy", "version.py")
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

if os.environ.get("TRAVIS_TAG", None):
    VERSION = os.environ["TRAVIS_TAG"]
elif os.environ.get("TRAVIS_BRANCH", None) in SNAPSHOT_BRANCHES:
    VERSION = os.environ["TRAVIS_BRANCH"]
else:
    print("Branch %s is not buildabranch - exiting." % os.environ.get("TRAVIS_BRANCH", None))
    sys.exit(0)

print("BUILD VERSION=%s" % VERSION)


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


def wheel_name() -> str:
    return "mitmproxy-{version}-py3-none-any.whl".format(version=VERSION)


def installer_name() -> str:
    ext = {
        "Windows": "exe",
        "Darwin": "dmg",
        "Linux": "run"
    }[platform.system()]
    return "mitmproxy-{version}-{platform}-installer.{ext}".format(
        version=VERSION,
        platform=PLATFORM_TAG,
        ext=ext,
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


@cli.command("info")
def info():
    print("Version: %s" % VERSION)


@cli.command("build")
def build():
    """
    Build a binary distribution
    """
    if exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    os.makedirs(DIST_DIR, exist_ok=True)

    for bdist, tools in sorted(BDISTS.items()):
        with Archive(join(DIST_DIR, archive_name(bdist))) as archive:
            for tool in tools:
                # We can't have a folder and a file with the same name.
                if tool == "mitmproxy":
                    tool = "mitmproxy_main"
                # This is PyInstaller, so it messes up paths.
                # We need to make sure that we are in the spec folder.
                with chdir(PYINSTALLER_SPEC):
                    print("Building %s binary..." % tool)
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

                print("> %s --version" % executable)
                print(subprocess.check_output([executable, "--version"]).decode())

                archive.add(executable, basename(executable))
        print("Packed {}.".format(archive_name(bdist)))


@cli.command("upload")
def upload():
    """
        Upload snapshot to snapshot server
    """
    subprocess.check_call(
        [
            "aws", "s3", "cp",
            "--acl", "public-read",
            DIST_DIR + "/",
            "s3://snapshots.mitmproxy.org/%s/" % VERSION,
            "--recursive",
        ]
    )


if __name__ == "__main__":
    cli()
