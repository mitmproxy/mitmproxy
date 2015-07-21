#!/usr/bin/env python

from os.path import dirname, realpath, join
from os import chdir, mkdir, getcwd
import os
import shutil
import subprocess
import tempfile
import glob
from shlex import split
from contextlib import contextmanager
import click

# https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
# scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
if os.name == "nt":
    venv_bin = "Scripts"
else:
    venv_bin = "bin"

_root_dir = join(dirname(realpath(__file__)), "..", "..")
projects = ("netlib", "pathod", "mitmproxy")
dirs = {x: join(_root_dir, x) for x in projects}
dirs["root"] = _root_dir
dirs["dist"] = join(dirs["mitmproxy"], "dist")

tools = ["mitmweb", "mitmdump", "pathod", "pathoc"]
if os.name != "nt":
    tools.append("mitmproxy")


# Python 3: replace with tempfile.TemporaryDirectory
@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    yield temp_workdir
    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


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
    with open(join(dirs["mitmproxy"], "CONTRIBUTORS"), "w") as f:
        f.write(contributors)


@cli.command("docs")
def render_docs():
    print("Rendering the docs...")
    subprocess.check_call([
        "cshape",
        join(dirs["mitmproxy"], "doc-src"),
        join(dirs["mitmproxy"], "doc")
    ])


@cli.command("release")
def build_release():
    # Make sure that the regular python installation is not on the python path!
    os.environ["PYTHONPATH"] = ""

    with tmpdir("mitmproxy_release") as tmp:

        print("Building release...")
        print("Temp directory: %s" % tmp)

        for project in projects:
            print("Creating %s source distribution..." % project)
            print(dirs[project])
            subprocess.check_call(["python", "./setup.py", "-q", "sdist", "--dist-dir", tmp, "--formats=gztar"], cwd=dirs[project])

        print("Creating virtualenv for test install...")
        venv_dir = join(tmp, "venv")
        subprocess.check_call(["virtualenv", "-q", venv_dir])

        pip = join(venv_dir, venv_bin, "pip")
        chdir(tmp)
        for project in projects:
            print("Installing %s..." % project)
            dist = glob.glob("./%s*" % project)[0]
            subprocess.check_call([pip, "install", "-q", dist])

        print("Running binaries...")
        for tool in tools:
            tool = join(venv_dir, venv_bin, tool)
            print(tool)
            print(subprocess.check_output([tool, "--version"]))

        shutil.rmtree(venv_dir)
        shutil.rmtree(dirs["dist"])
        shutil.copytree(tmp, dirs["dist"])

        # TODO: Use the output of this step for further processing, i.e. test and then uplaod using twine
        # https://packaging.python.org/en/latest/distributing.html#upload-your-distributions
        # https://github.com/pypa/twine/issues/116


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
        "%s/*" % dirs["dist"]
    ])

if __name__ == "__main__":
    cli()
