#!/usr/bin/env python3

import contextlib
import fnmatch
import os
import sys
import platform
import re
import runpy
import shlex
import subprocess
import tarfile
import zipfile
from os.path import join, abspath, dirname

import click
import pysftp

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


def git(args: str) -> str:
    with chdir(ROOT_DIR):
        return subprocess.check_output(["git"] + shlex.split(args)).decode()


def get_version(dev: bool = False, build: bool = False) -> str:
    x = runpy.run_path(VERSION_FILE)
    return x["get_version"](dev, build, True)


def archive_name(bdist: str) -> str:
    if platform.system() == "Windows":
        ext = "zip"
    else:
        ext = "tar.gz"
    return "{project}-{version}-{platform}.{ext}".format(
        project=bdist,
        version=get_version(),
        platform=PLATFORM_TAG,
        ext=ext
    )


def wheel_name() -> str:
    return "mitmproxy-{version}-py3-none-any.whl".format(
        version=get_version(True),
    )


def installer_name() -> str:
    ext = {
        "Windows": "exe",
        "Darwin": "dmg",
        "Linux": "run"
    }[platform.system()]
    return "mitmproxy-{version}-{platform}-installer.{ext}".format(
        version=get_version(),
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


@cli.command("contributors")
def contributors():
    """
    Update CONTRIBUTORS.md
    """
    with chdir(ROOT_DIR):
        print("Updating CONTRIBUTORS...")
        contributors_data = git("shortlog -n -s")
        with open("CONTRIBUTORS", "wb") as f:
            f.write(contributors_data.encode())


@cli.command("upload-release")
@click.option('--username', prompt=True)
@click.password_option(confirmation_prompt=False)
@click.option('--repository', default="pypi")
def upload_release(username, password, repository):
    """
    Upload wheels to PyPI
    """
    filename = wheel_name()
    print("Uploading {} to {}...".format(filename, repository))
    subprocess.check_call([
        "twine",
        "upload",
        "-u", username,
        "-p", password,
        "-r", repository,
        join(DIST_DIR, filename)
    ])


@cli.command("homebrew-pr")
def homebrew_pr():
    """
    Create a new Homebrew PR
    """
    if platform.system() != "Darwin":
        print("You need to run this on macOS to create a new Homebrew PR. Sorry.")
        sys.exit(1)

    print("Creating a new PR with Homebrew...")
    subprocess.check_call([
        "brew",
        "bump-formula-pr",
        "--url", "https://github.com/mitmproxy/mitmproxy/archive/v{}".format(get_version()),
        "mitmproxy",
    ])


if __name__ == "__main__":
    cli()
