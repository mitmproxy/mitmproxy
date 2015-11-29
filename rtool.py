#!/usr/bin/env python
from __future__ import absolute_import, print_function, division

from os.path import join
import contextlib
import os
import shutil
import subprocess
import glob
import re
import shlex
import runpy
import pprint
from zipfile import ZipFile
from tarfile import TarFile
import platform

import click

# https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
# scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
if platform.system() == "Windows":
    VENV_BIN = "Scripts"
else:
    VENV_BIN = "bin"

if platform.system() == "Windows":
    def Archive(name):
        a = ZipFile(name + ".zip","w")
        a.add = a.write
        return a
else:
    def Archive(name):
        a = TarFile(name + ".tar.gz", "w:gz")
        return a


RELEASE_DIR = join(os.path.dirname(os.path.realpath(__file__)))
DIST_DIR = join(RELEASE_DIR, "dist")
ROOT_DIR = join(RELEASE_DIR, "..")

BUILD_DIR = join(RELEASE_DIR, "build")
PYINSTALLER_TEMP = join(BUILD_DIR, "pyinstaller")
PYINSTALLER_DIST = join(BUILD_DIR, "binaries")

VENV_DIR = join(BUILD_DIR, "venv")
VENV_PIP = join(VENV_DIR, VENV_BIN, "pip")
VENV_PYINSTALLER = join(VENV_DIR, VENV_BIN, "pyinstaller")


ALL_PROJECTS = {
    "netlib": {
        "tools": [],
        "vfile": join(ROOT_DIR, "netlib/netlib/version.py"),
        "dir": join(ROOT_DIR, "netlib")
    },
    "pathod": {
        "tools": ["pathod", "pathoc"],
        "vfile": join(ROOT_DIR, "pathod/libpathod/version.py"),
        "dir": join(ROOT_DIR, "pathod")
    },
    "mitmproxy": {
        "tools": ["mitmproxy", "mitmdump", "mitmweb"],
        "vfile": join(ROOT_DIR, "mitmproxy/libmproxy/version.py"),
        "dir": join(ROOT_DIR, "mitmproxy")
    }
}
if platform.system() == "Windows":
    ALL_PROJECTS["mitmproxy"]["tools"].remove("mitmproxy")

projects = {}

def version(project):
    return runpy.run_path(projects[project]["vfile"])["VERSION"]

def sdist_name(project):
	return "{project}-{version}.tar.gz".format(project=project, version=version(project))

@contextlib.contextmanager
def empty_pythonpath():
    """
    Make sure that the regular python installation is not on the python path,
    which would give us access to modules installed outside of our virtualenv.
    """
    pythonpath = os.environ.get("PYTHONPATH","")
    os.environ["PYTHONPATH"] = ""
    yield
    os.environ["PYTHONPATH"] = pythonpath


@contextlib.contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


@click.group(chain=True)
@click.option(
    '--project', '-p',
    multiple=True, type=click.Choice(ALL_PROJECTS.keys()), default=ALL_PROJECTS.keys()
)
def cli(project):
    """
    mitmproxy build tool
    """
    for name in project:
        projects[name] = ALL_PROJECTS[name]

@cli.command("contributors")
def contributors():
    """
    Update CONTRIBUTORS.md
    """
    for project, conf in projects.items():
        with chdir(conf["dir"]):
            print("Updating %s/CONTRIBUTORS..." % project)
            contributors_data = subprocess.check_output(
                shlex.split("git shortlog -n -s")
            )
            with open("CONTRIBUTORS", "w") as f:
                f.write(contributors_data)

@cli.command("set-version")
@click.argument('version')
def set_version(version):
    """
    Update version information
    """
    print("Update versions...")
    version = ", ".join(version.split("."))
    for p, conf in projects.items():
        print("Update %s..." % os.path.normpath(conf["vfile"]))
        with open(conf["vfile"], "rb") as f:
            content = f.read()
        new_content = re.sub(
            r"IVERSION\s*=\s*\([\d,\s]+\)", "IVERSION = (%s)" % version,
            content
        )
        with open(conf["vfile"], "wb") as f:
            f.write(new_content)


@cli.command("git")
@click.argument('args', nargs=-1, required=True)
def git(args):
    """
    Run a git command on every project
    """
    args = ["git"] + list(args)
    for project, conf in projects.items():
        print("%s> %s..." % (project, " ".join(args)))
        subprocess.check_call(
            args,
            cwd=conf["dir"]
        )


@cli.command("sdist")
def sdist():
    """
    Build a source distribution
    """
    with empty_pythonpath():
        print("Building release...")
        if os.path.exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)
        for project, conf in projects.items():
            print("Creating %s source distribution..." % project)
            subprocess.check_call(
                [
                    "python", "./setup.py",
                    "-q", "sdist", "--dist-dir", DIST_DIR, "--formats=gztar"
                ],
                cwd=conf["dir"]
            )

        print("Creating virtualenv for test install...")
        if os.path.exists(VENV_DIR):
            shutil.rmtree(VENV_DIR)
        subprocess.check_call(["virtualenv", "-q", VENV_DIR])

        with chdir(DIST_DIR):
            for project, conf in projects.items():
                print("Installing %s..." % project)
                subprocess.check_call([VENV_PIP, "install", "-q", sdist_name(project)])

            print("Running binaries...")
            for project, conf in projects.items():
                for tool in conf["tools"]:
                    tool = join(VENV_DIR, VENV_BIN, tool)
                    print("> %s --version" % tool)
                    print(subprocess.check_output([tool, "--version"]))

            print("Virtualenv available for further testing:")
            print("source %s" % os.path.normpath(join(VENV_DIR, VENV_BIN, "activate")))


@cli.command("bdist")
@click.option('--use-existing-sdist/--no-use-existing-sdist', default=False)
@click.pass_context
def bdist(ctx, use_existing_sdist):
    """
    Build a binary distribution
    """
    if os.path.exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if os.path.exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    if not use_existing_sdist:
        ctx.invoke(sdist)

    print("Installing PyInstaller...")
    subprocess.check_call([VENV_PIP, "install", "-q", "PyInstaller~=3.0.0"])

    for p, conf in projects.items():
        if conf["tools"]:
            archive_name = "{project}-{version}-{platform}".format(
                project=p, 
                version=version(p), 
                platform=platform.system()
            )
            with Archive(join(DIST_DIR, archive_name)) as archive:
                for tool in conf["tools"]:
                    spec = join(conf["dir"], "release", "%s.spec" % tool)
                    print("Building %s binary..." % tool)
                    subprocess.check_call(
                        [
                            VENV_PYINSTALLER,
                            "--clean",
                            "--workpath", PYINSTALLER_TEMP,
                            "--distpath", PYINSTALLER_DIST,
                            # This is PyInstaller, so setting a 
                            # different log level obviously breaks it :-)
                            # "--log-level", "WARN",
                            spec
                        ]
                    )

                    # Test if it works at all O:-)
                    executable = join(PYINSTALLER_DIST, tool)
                    if platform.system() == "Windows":
                        executable += ".exe"
                    print("Testinng %s..." % executable)
                    subprocess.check_call([executable, "--version"])

                    archive.add(executable, os.path.basename(executable))


@cli.command("upload")
@click.option('--username', prompt=True)
@click.password_option(confirmation_prompt=False)
@click.option('--repository', default="pypi")
def upload_release(username, password, repository):
    """
    Upload source distributions to PyPI
    """
    
    for project in projects.keys():
	    print("Uploading {} to {}...".format(project, repository))
	    subprocess.check_call([
	        "twine",
	        "upload",
	        "-u", username,
	        "-p", password,
	        "-r", repository,
	        join(DIST_DIR, sdist_name(project))
	    ])


@cli.command("wizard")
@click.option('--version', prompt=True)
@click.option('--username', prompt="PyPI Username")
@click.password_option(confirmation_prompt=False, prompt="PyPI Password")
@click.option('--repository', default="pypi")
@click.pass_context
def wizard(ctx, version, username, password, repository):
    """
    Interactive Release Wizard
    """
    for project, conf in projects.items():
        is_dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=conf["dir"])
        if is_dirty:
            raise RuntimeError("%s repository is not clean." % project)

    # Build test release
    ctx.invoke(bdist)
    click.confirm("Please test the release now. Is it ok?", abort=True)

    # bump version, update docs and contributors
    ctx.invoke(set_version, version=version)
    ctx.invoke(contributors)

    # version bump commit + tag
    ctx.invoke(
        git, args=["commit", "-a", "-m", "bump version"]
    )
    ctx.invoke(git, args=["tag", version])
    ctx.invoke(git, args=["push"])
    ctx.invoke(git, args=["push", "--tags"])

    # Re-invoke sdist with bumped version
    ctx.invoke(sdist)
    click.confirm("All good, can upload sdist to PyPI?", abort=True)
    ctx.invoke(
        upload_release,
        username=username, password=password, repository=repository
    )
    click.echo("All done!")


if __name__ == "__main__":
    cli()
