#!/usr/bin/env python3

import contextlib
import os
import sys
import platform
import runpy
import shlex
import subprocess
from os.path import join, abspath, dirname

import cryptography.fernet
import click


ROOT_DIR = abspath(join(dirname(__file__), ".."))
RELEASE_DIR = join(ROOT_DIR, "release")
DIST_DIR = join(RELEASE_DIR, "dist")
VERSION_FILE = join(ROOT_DIR, "mitmproxy", "version.py")


def git(args: str) -> str:
    with chdir(ROOT_DIR):
        return subprocess.check_output(["git"] + shlex.split(args)).decode()


def get_version(dev: bool = False, build: bool = False) -> str:
    x = runpy.run_path(VERSION_FILE)
    return x["get_version"](dev, build, True)


def wheel_name() -> str:
    return "mitmproxy-{version}-py3-none-any.whl".format(
        version=get_version(True),
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


@cli.command("encrypt")
@click.argument('infile', type=click.File('rb'))
@click.argument('outfile', type=click.File('wb'))
@click.argument('key', envvar='RTOOL_KEY')
def encrypt(infile, outfile, key):
    f = cryptography.fernet.Fernet(key.encode())
    outfile.write(f.encrypt(infile.read()))


if __name__ == "__main__":
    cli()
