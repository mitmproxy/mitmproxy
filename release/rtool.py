#!/usr/bin/env python
from __future__ import absolute_import, print_function, division
from os.path import join
import contextlib
import os
import shutil
import subprocess
import re
import shlex
import runpy
import zipfile
import tarfile
import platform
import click
import pysftp
import fnmatch

# https://virtualenv.pypa.io/en/latest/userguide.html#windows-notes
# scripts and executables on Windows go in ENV\Scripts\ instead of ENV/bin/
if platform.system() == "Windows":
    VENV_BIN = "Scripts"
else:
    VENV_BIN = "bin"

if platform.system() == "Windows":
    def Archive(name):
        a = zipfile.ZipFile(name, "w")
        a.add = a.write
        return a
else:
    def Archive(name):
        return tarfile.open(name, "w:gz")

RELEASE_DIR = join(os.path.dirname(os.path.realpath(__file__)))
DIST_DIR = join(RELEASE_DIR, "dist")
ROOT_DIR = os.path.normpath(join(RELEASE_DIR, ".."))
RELEASE_SPEC_DIR = join(RELEASE_DIR, "specs")
VERSION_FILE = join(ROOT_DIR, "netlib/version.py")

BUILD_DIR = join(RELEASE_DIR, "build")
PYINSTALLER_TEMP = join(BUILD_DIR, "pyinstaller")
PYINSTALLER_DIST = join(BUILD_DIR, "binaries")

VENV_DIR = join(BUILD_DIR, "venv")
VENV_PIP = join(VENV_DIR, VENV_BIN, "pip")
VENV_PYINSTALLER = join(VENV_DIR, VENV_BIN, "pyinstaller")

project = {
    "name": "mitmproxy",
    "tools": ["pathod", "pathoc", "mitmproxy", "mitmdump", "mitmweb"],
    "bdists": {
        "mitmproxy": ["mitmproxy", "mitmdump", "mitmweb"],
        "pathod": ["pathoc", "pathod"]
    },
    "dir": ROOT_DIR,
    "python_version": "py2"
}
if platform.system() == "Windows":
    project["tools"].remove("mitmproxy")
    project["bdists"]["mitmproxy"].remove("mitmproxy")


def get_version():
    return runpy.run_path(VERSION_FILE)["VERSION"]


def get_snapshot_version():
    last_tag, tag_dist, commit = git("describe --tags --long").strip().rsplit(b"-", 2)
    tag_dist = int(tag_dist)
    if tag_dist == 0:
        return get_version()
    else:
        # The wheel build tag (we use the commit) must start with a digit, so we include "0x"
        return "{version}dev{tag_dist:04}-0x{commit}".format(
            version=get_version(),  # this should already be the next version
            tag_dist=tag_dist,
            commit=commit
        )


def archive_name(project):
    platform_tag = {
        "Darwin": "osx",
        "Windows": "win32",
        "Linux": "linux"
    }.get(platform.system(), platform.system())
    if platform.system() == "Windows":
        ext = "zip"
    else:
        ext = "tar.gz"
    return "{project}-{version}-{platform}.{ext}".format(
        project=project,
        version=get_version(),
        platform=platform_tag,
        ext=ext
    )


def wheel_name():
    return "{project}-{version}-{py_version}-none-any.whl".format(
        project=project["name"],
        version=get_version(),
        py_version=project["python_version"]
    )


@contextlib.contextmanager
def empty_pythonpath():
    """
    Make sure that the regular python installation is not on the python path,
    which would give us access to modules installed outside of our virtualenv.
    """
    pythonpath = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = ""
    yield
    os.environ["PYTHONPATH"] = pythonpath


@contextlib.contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def git(args):
    with chdir(ROOT_DIR):
        return subprocess.check_output(["git"] + shlex.split(args))


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
    print("Update %s..." % VERSION_FILE)
    with open(VERSION_FILE, "rb") as f:
        content = f.read()
    new_content = re.sub(
        r"IVERSION\s*=\s*\([\d,\s]+\)", "IVERSION = (%s)" % version,
        content
    )
    with open(VERSION_FILE, "wb") as f:
        f.write(new_content)


@cli.command("wheels")
def wheels():
    """
    Build wheels
    """
    with empty_pythonpath():
        print("Building release...")
        if os.path.exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)

        print("Creating wheel for %s ..." % project["name"])
        subprocess.check_call(
            [
                "python", "./setup.py", "-q",
                "bdist_wheel", "--dist-dir", DIST_DIR,
            ],
            cwd=project["dir"]
        )

        print("Creating virtualenv for test install...")
        if os.path.exists(VENV_DIR):
            shutil.rmtree(VENV_DIR)
        subprocess.check_call(["virtualenv", "-q", VENV_DIR])

        with chdir(DIST_DIR):
            print("Installing %s..." % project["name"])
            subprocess.check_call([VENV_PIP, "install", "-q", wheel_name()])

            print("Running binaries...")
            for tool in project["tools"]:
                tool = join(VENV_DIR, VENV_BIN, tool)
                print("> %s --version" % tool)
                print(subprocess.check_output([tool, "--version"]))

            print("Virtualenv available for further testing:")
            print("source %s" % os.path.normpath(join(VENV_DIR, VENV_BIN, "activate")))


@cli.command("bdist")
@click.option("--use-existing-wheels/--no-use-existing-wheels", default=False)
@click.argument("pyinstaller_version", envvar="PYINSTALLER_VERSION", default="PyInstaller~=3.1.1")
@click.pass_context
def bdist(ctx, use_existing_wheels, pyinstaller_version):
    """
    Build a binary distribution
    """
    if os.path.exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if os.path.exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    if not use_existing_wheels:
        ctx.invoke(wheels)

    print("Installing PyInstaller...")
    subprocess.check_call([VENV_PIP, "install", "-q", pyinstaller_version])

    for bdist_project, tools in project["bdists"].items():
        with Archive(join(DIST_DIR, archive_name(bdist_project))) as archive:
            for tool in tools:
                # This is PyInstaller, so it messes up paths.
                # We need to make sure that we are in the spec folder.
                with chdir(RELEASE_SPEC_DIR):
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
                            "%s.spec" % tool
                        ]
                    )

                # Test if it works at all O:-)
                executable = join(PYINSTALLER_DIST, tool)
                if platform.system() == "Windows":
                    executable += ".exe"
                print("> %s --version" % executable)
                subprocess.check_call([executable, "--version"])

                archive.add(executable, os.path.basename(executable))
        print("Packed {}.".format(archive_name(bdist_project)))


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


@cli.command("upload-snapshot")
@click.option("--host", envvar="SNAPSHOT_HOST", prompt=True)
@click.option("--port", envvar="SNAPSHOT_PORT", type=int, default=22)
@click.option("--user", envvar="SNAPSHOT_USER", prompt=True)
@click.option("--private-key", default=join(RELEASE_DIR, "rtool.pem"))
@click.option("--private-key-password", envvar="SNAPSHOT_PASS", prompt=True, hide_input=True)
@click.option("--wheel/--no-wheel", default=False)
@click.option("--bdist/--no-bdist", default=False)
def upload_snapshot(host, port, user, private_key, private_key_password, wheel, bdist):
    """
    Upload snapshot to snapshot server
    """
    with pysftp.Connection(host=host,
                           port=port,
                           username=user,
                           private_key=private_key,
                           private_key_pass=private_key_password) as sftp:

            dir_name = "snapshots/v{}".format(get_version())
            sftp.makedirs(dir_name)
            with sftp.cd(dir_name):
                files = []
                if wheel:
                    files.append(wheel_name())
                for bdist in project["bdists"].keys():
                    files.append(archive_name(bdist))

                for f in files:
                    local_path = join(DIST_DIR, f)
                    remote_filename = f.replace(get_version(), get_snapshot_version())
                    symlink_path = "../{}".format(f.replace(get_version(), "latest"))

                    # Delete old versions
                    old_version = f.replace(get_version(), "*")
                    for f_old in sftp.listdir():
                        if fnmatch.fnmatch(f_old, old_version):
                            print("Removing {}...".format(f_old))
                            sftp.remove(f_old)

                    # Upload new version
                    print("Uploading {} as {}...".format(f, remote_filename))
                    with click.progressbar(length=os.stat(local_path).st_size) as bar:
                        sftp.put(
                            local_path,
                            "." + remote_filename,
                            callback=lambda done, total: bar.update(done - bar.pos)
                        )
                        # We hide the file during upload.
                        sftp.rename("." + remote_filename, remote_filename)

                    # update symlink for the latest release
                    if sftp.lexists(symlink_path):
                        print("Removing {}...".format(symlink_path))
                        sftp.remove(symlink_path)
                    sftp.symlink("v{}/{}".format(get_version(), remote_filename), symlink_path)


@cli.command("wizard")
@click.option('--next-version', prompt=True)
@click.option('--username', prompt="PyPI Username")
@click.password_option(confirmation_prompt=False, prompt="PyPI Password")
@click.option('--repository', default="pypi")
@click.pass_context
def wizard(ctx, next_version, username, password, repository):
    """
    Interactive Release Wizard
    """
    is_dirty = git("status --porcelain")
    if is_dirty:
        raise RuntimeError("Repository is not clean.")

    # update contributors file
    ctx.invoke(contributors)

    # Build test release
    ctx.invoke(bdist)

    try:
        click.confirm("Please test the release now. Is it ok?", abort=True)
    except click.Abort:
        # undo changes
        git("checkout CONTRIBUTORS")
        raise

    # Everything ok - let's ship it!
    git("tag v{}".format(get_version()))
    git("push --tags")
    ctx.invoke(
        upload_release,
        username=username, password=password, repository=repository
    )

    click.confirm("Now please wait until CI has built binaries. Finished?")

    # version bump commit
    ctx.invoke(set_version, version=next_version)
    git("commit -a -m \"bump version\"")
    git("push")

    click.echo("All done!")


if __name__ == "__main__":
    cli()
