#!/usr/bin/env python

from os.path import dirname, realpath, join, exists, normpath
from os import chdir
import os
import shutil
import subprocess
import glob
import re
from shlex import split
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
tools = ["mitmproxy", "mitmdump", "mitmweb", "pathod", "pathoc"]
if os.name == "nt":
    tools.remove("mitmproxy")

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
def contributors():
    """
    Update CONTRIBUTORS.md
    """
    print("Updating CONTRIBUTORS.md...")
    contributors_data = subprocess.check_output(split("git shortlog -n -s"))
    with open(join(mitmproxy_dir, "CONTRIBUTORS"), "w") as f:
        f.write(contributors_data)


@cli.command("docs")
def docs():
    """
    Render the docs
    """
    print("Rendering the docs...")
    subprocess.check_call([
        "cshape",
        join(mitmproxy_dir, "doc-src"),
        join(mitmproxy_dir, "doc")
    ])


@cli.command("set-version")
@click.argument('version')
def set_version(version):
    """
    Update version information
    """
    print("Update versions...")
    version = ", ".join(version.split("."))
    for version_file in version_files:
        print("Update %s..." % version_file)
        with open(version_file, "rb") as f:
            content = f.read()
        new_content = re.sub(r"IVERSION\s*=\s*\([\d,\s]+\)", "IVERSION = (%s)" % version, content)
        with open(version_file, "wb") as f:
            f.write(new_content)


@cli.command("git")
@click.argument('args', nargs=-1, required=True)
def git(args):
    """
    Run a git command on every project
    """
    args = ["git"] + list(args)
    for project in projects:
        print("%s> %s..." % (project, " ".join(args)))
        subprocess.check_call(
            args,
            cwd=join(root_dir, project)
        )


@cli.command("sdist")
def sdist():
    """
    Build a source distribution
    """
    # Make sure that the regular python installation is not on the python path!
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


@cli.command("test")
@click.pass_context
def test(ctx):
    """
    Test the source distribution
    """
    if not exists(dist_dir):
        ctx.invoke(sdist)

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
    print("source %s" % normpath(join(test_venv_dir, venv_bin, "activate")))


@cli.command("upload")
@click.option('--username', prompt=True)
@click.password_option(confirmation_prompt=False)
@click.option('--repository', default="pypi")
def upload_release(username, password, repository):
    """
    Upload source distributions to PyPI
    """
    print("Uploading distributions...")
    subprocess.check_call([
        "twine",
        "upload",
        "-u", username,
        "-p", password,
        "-r", repository,
        "%s/*" % dist_dir
    ])


"""

TODO: Fully automate build process.
This skeleton is missing OSX builds and updating mitmproxy.org.


@cli.command("wizard")
@click.option('--version', prompt=True)
@click.option('--username', prompt=True)
@click.password_option(confirmation_prompt=False)
@click.option('--repository', default="pypi")
@click.option('--test/--no-test', default=True)
@click.pass_context
def wizard(ctx, version, username, password, repository, test):
    ""
    Interactive Release Wizard
    ""

    for project in projects:
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=join(root_dir, project)):
            raise RuntimeError("%s repository is not clean." % project)

    if test:
        ctx.invoke(sdist)
        ctx.invoke(test)
        click.confirm("Please test the release now. Is it ok?", abort=True)

    ctx.invoke(set_version, version=version)
    ctx.invoke(docs)
    ctx.invoke(contributors)

    ctx.invoke(git, args=["commit", "-a", "-m", "bump version"])
    ctx.invoke(git, args=["tag", "v" + version])
    ctx.invoke(git, args=["push", "--tags"])
    ctx.invoke(sdist)
    ctx.invoke(upload_release, username=username, password=password, repository=repository)
    click.echo("All done!")
"""

if __name__ == "__main__":
    cli()
