#!/usr/bin/env python3

import contextlib
import fnmatch
import os
import platform
import runpy
import shlex
import shutil
import subprocess
import tarfile
import zipfile
from os.path import join, abspath, normpath, dirname, exists, basename
from typing import Union

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

ROOT_DIR = abspath(join(dirname(__file__), ".."))
RELEASE_DIR = join(ROOT_DIR, "release")

BUILD_DIR = join(RELEASE_DIR, "build")
DIST_DIR = join(RELEASE_DIR, "dist")

PYINSTALLER_SPEC = join(RELEASE_DIR, "specs")
# PyInstaller 3.2 does not bundle pydivert's Windivert binaries
PYINSTALLER_HOOKS = join(RELEASE_DIR, "hooks")
PYINSTALLER_TEMP = join(BUILD_DIR, "pyinstaller")
PYINSTALLER_DIST = join(BUILD_DIR, "binaries")

VENV_DIR = join(BUILD_DIR, "venv")

# Project Configuration
VERSION_FILE = join(ROOT_DIR, "mitmproxy", "version.py")
PROJECT_NAME = "mitmproxy"
PYTHON_VERSION = "py3"
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


def get_version() -> str:
    return runpy.run_path(VERSION_FILE)["VERSION"]


def git(args: str) -> str:
    with chdir(ROOT_DIR):
        return subprocess.check_output(["git"] + shlex.split(args)).decode()


def build_venv(args: Union[str, list]):
    if not isinstance(args, list):
        args = shlex.split(args)
    args[0] = join(VENV_DIR, VENV_BIN, args[0])

    click.secho("(build-venv) > {}".format(" ".join(args)), color="cyan")
    subprocess.check_call(
        args,
        env={
            **os.environ,
            "VIRTUAL_ENV": VENV_DIR,
            "PYTHON_HOME": "",
        }
    )


def get_snapshot_version() -> str:
    last_tag, tag_dist, commit = git("describe --tags --long").strip().rsplit("-", 2)
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


def archive_name(bdist: str) -> str:
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
        project=bdist,
        version=get_version(),
        platform=platform_tag,
        ext=ext
    )


def wheel_name() -> str:
    return "{project}-{version}-{py_version}-none-any.whl".format(
        project=PROJECT_NAME,
        version=get_version(),
        py_version=PYTHON_VERSION
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


@cli.command("wheel")
def make_wheel():
    """
    Build wheel
    """
    with empty_pythonpath():
        if exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)

        click.secho("Creating wheel...", color="cyan")
        subprocess.check_call(
            [
                "python3", "./setup.py", "-q",
                "bdist_wheel", "--dist-dir", DIST_DIR,
            ],
            cwd=ROOT_DIR
        )

        if exists(VENV_DIR):
            click.secho("Removing old virtualenv for test install...", color="cyan")
            shutil.rmtree(VENV_DIR)

        click.secho("Creating new virtualenv for test install...", color="cyan")
        subprocess.check_call(["python3", "-m", "virtualenv", "-q", "--always-copy", VENV_DIR])

        with chdir(DIST_DIR):
            click.secho("Install wheel into virtualenv...", color="cyan")
            # lxml...
            if platform.system() == "Windows":
                build_venv(
                    "pip install -q https://snapshots.mitmproxy.org/misc/lxml-3.6.0-cp35-cp35m-win32.whl")
            build_venv("pip install -q {}".format(wheel_name()))

            click.secho("Running tools...", color="cyan")
            for tool in TOOLS:
                build_venv("{} --version".format(tool))

            print("Virtualenv available for further testing:")
            print("source %s" % normpath(join(VENV_DIR, VENV_BIN, "activate")))


@cli.command("bdist")
@click.option("--use-existing-wheel/--no-use-existing-wheel", default=False)
@click.option("--use-existing-pyinstaller/--no-use-existing-pyinstaller", default=False)
@click.argument(
    "pyinstaller_version",
    envvar="PYINSTALLER_VERSION",
    # the next commit after this updates the bootloaders, which then segfault! 🎉
    # https://github.com/pyinstaller/pyinstaller/issues/2232
    default="git+https://github.com/pyinstaller/pyinstaller.git@e78b7013382afebc7410901e066e4d4eb8432cd7"
    # 3.2.0 is broken. 🎉
    # This one may also still work:
    # default="PyInstaller~=3.1.1"
)
@click.argument("setuptools_version", envvar="SETUPTOOLS_VERSION",
                default="setuptools>=25.1.0,!=25.1.1,!=29.0.0")
@click.pass_context
def make_bdist(ctx, use_existing_wheel, use_existing_pyinstaller, pyinstaller_version,
               setuptools_version):
    """
    Build a binary distribution
    """
    if exists(PYINSTALLER_TEMP):
        shutil.rmtree(PYINSTALLER_TEMP)
    if exists(PYINSTALLER_DIST):
        shutil.rmtree(PYINSTALLER_DIST)

    if not use_existing_wheel:
        ctx.invoke(make_wheel)

    if not use_existing_pyinstaller:
        print("Installing PyInstaller and setuptools...")
        build_venv("pip install {} {}".format(pyinstaller_version, setuptools_version))

    build_venv("pip freeze")

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
                    build_venv(
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
                if executable.startswith("mitmproxy_main"):
                    shutil.move(
                        executable,
                        executable.replace("_main", "")
                    )
                    executable = executable.replace("_main", "")

                print("> %s --version" % executable)
                print(subprocess.check_output([executable, "--version"]).decode())

                archive.add(executable, basename(executable))
        print("Packed {}.".format(archive_name(bdist)))


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
            if bdist:
                for bdist in sorted(BDISTS.keys()):
                    files.append(archive_name(bdist))

            for f in files:
                local_path = join(DIST_DIR, f)
                remote_filename = f.replace(get_version(), get_snapshot_version())
                symlink_path = "../{}".format(f.replace(get_version(), "latest"))

                # Upload new version
                print("Uploading {} as {}...".format(f, remote_filename))
                with click.progressbar(length=os.stat(local_path).st_size) as bar:
                    # We hide the file during upload
                    sftp.put(
                        local_path,
                        "." + remote_filename,
                        callback=lambda done, total: bar.update(done - bar.pos)
                    )

                # Delete old versions
                old_version = f.replace(get_version(), "*")
                for f_old in sftp.listdir():
                    if fnmatch.fnmatch(f_old, old_version):
                        print("Removing {}...".format(f_old))
                        sftp.remove(f_old)

                # Show new version
                sftp.rename("." + remote_filename, remote_filename)

                # update symlink for the latest release
                if sftp.lexists(symlink_path):
                    print("Removing {}...".format(symlink_path))
                    sftp.remove(symlink_path)
                if f != wheel_name():
                    # "latest" isn't a proper wheel version, so this could not be installed.
                    # https://github.com/mitmproxy/mitmproxy/issues/1065
                    sftp.symlink("v{}/{}".format(get_version(), remote_filename), symlink_path)


if __name__ == "__main__":
    cli()
