#!/usr/bin/env python

from os.path import dirname, realpath, join, exists, normpath
from os import chdir, mkdir, getcwd
import os
import shutil
import subprocess
import tempfile
import glob
import re
from shlex import split
from contextlib import contextmanager
import click

# https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
# scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
if os.name == "nt":
    venv_bin = "Scripts"
else:
    venv_bin = "bin"

root_dir = join(dirname(realpath(__file__)), "..", "..")
mitmproxy_dir = join(root_dir, "mitmproxy")
dist_dir = join(mitmproxy_dir, "dist")
test_venv_dir = join(root_dir, "venv.mitmproxy-release")

projects = ("netlib", "pathod", "mitmproxy")
tools = ["mitmweb", "mitmdump", "pathod", "pathoc"]
if os.name != "nt":
    tools.append("mitmproxy")

version_files = (join(root_dir, x) for x in (
    "mitmproxy/libmproxy/version.py",
    "pathod/libpathod/version.py",
    "netlib/netlib/version.py"
))

@click.group(chain=True)
def cli():
    """
    mitmproxy build tool
    """
    pass


@cli.command("contributors")
def update_contributors():
    print("Updating CONTRIBUTORS.md...")
    contributors = subprocess.check_output(split("git shortlog -n -s"))
    with open(join(mitmproxy_dir, "CONTRIBUTORS"), "w") as f:
        f.write(contributors)


@cli.command("docs")
def render_docs():
    print("Rendering the docs...")
    subprocess.check_call([
        "cshape",
        join(mitmproxy_dir, "doc-src"),
        join(mitmproxy_dir, "doc")
    ])


@cli.command("test")
@click.pass_context
def test(ctx):
    if not exists(dist_dir):
        ctx.invoke(release)

    # Make sure that the regular python installation is not on the python path!
    os.environ["PYTHONPATH"] = ""

    print("Creating virtualenv for test install...")
    if exists(test_venv_dir):
        shutil.rmtree(test_venv_dir)
    subprocess.check_call(["virtualenv", "-q", test_venv_dir])

    pip = join(test_venv_dir, venv_bin, "pip")
    chdir(dist_dir)
    for project in projects:
        print("Installing %s..." % project)
        dist = glob.glob("./%s*" % project)[0]
        subprocess.check_call([pip, "install", "-q", dist])

    print("Running binaries...")
    for tool in tools:
        tool = join(test_venv_dir, venv_bin, tool)
        print(tool)
        print(subprocess.check_output([tool, "--version"]))

    print("Virtualenv available for further testing:")
    print(normpath(join(test_venv_dir, venv_bin, "activate")))


@cli.command("release")
def release():
    os.environ["PYTHONPATH"] = ""

    print("Building release...")

    if exists(dist_dir):
        shutil.rmtree(dist_dir)
    for project in projects:
        print("Creating %s source distribution..." % project)
        subprocess.check_call(
            ["python", "./setup.py", "-q", "sdist", "--dist-dir", dist_dir, "--formats=gztar"],
            cwd=join(root_dir, project)
        )


@cli.command("set-version")
@click.argument('version')
def set_version(version):
    version = ", ".join(version.split("."))
    for version_file in version_files:
        with open(version_file, "rb") as f:
            content = f.read()
        new_content = re.sub(r"IVERSION\s*=\s*\([\d,\s]+\)", "IVERSION = (%s)" % version, content)
        with open(version_file, "wb") as f:
            f.write(new_content)


@cli.command("add-tag")
@click.argument('version')
def git_tag(version):
    for project in projects:
        print("Tagging %s..." % project)
        subprocess.check_call(
            ["git", "tag", version],
            cwd=join(root_dir, project)
        )
        subprocess.check_call(
            ["git", "push", "--tags"],
            cwd=join(root_dir, project)
        )


@cli.command("upload")
@click.option('--username', prompt=True)
@click.password_option(confirmation_prompt=False)
@click.option('--repository', default="pypi")
def upload_release(username, password, repository):
    print("Uploading distributions...")
    subprocess.check_call([
        "twine",
        "upload",
        "-u", username,
        "-p", password,
        "-r", repository,
        "%s/*" % dist_dir
    ])


if __name__ == "__main__":
    cli()
