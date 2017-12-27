#!/usr/bin/env python3

import contextlib
import fnmatch
import os
import platform
import re
import runpy
import shlex
import shutil
import subprocess
import tarfile
import zipfile
from os.path import join, abspath, dirname, exists, basename

import click
import cryptography.fernet
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


def set_version(dev: bool) -> None:
    """
    Update version information in mitmproxy's version.py to either include hardcoded information or not.
    """
    version = get_version(dev, dev)
    with open(VERSION_FILE, "r") as f:
        content = f.read()
    content = re.sub(r'^VERSION = ".+?"', 'VERSION = "{}"'.format(version), content, flags=re.M)
    with open(VERSION_FILE, "w") as f:
        f.write(content)


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


@cli.command("encrypt")
@click.argument('infile', type=click.File('rb'))
@click.argument('outfile', type=click.File('wb'))
@click.argument('key', envvar='RTOOL_KEY')
def encrypt(infile, outfile, key):
    f = cryptography.fernet.Fernet(key.encode())
    outfile.write(f.encrypt(infile.read()))


@cli.command("decrypt")
@click.argument('infile', type=click.File('rb'))
@click.argument('outfile', type=click.File('wb'))
@click.argument('key', envvar='RTOOL_KEY')
def decrypt(infile, outfile, key):
    f = cryptography.fernet.Fernet(key.encode())
    outfile.write(f.decrypt(infile.read()))


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
    Build a Python wheel
    """
    set_version(True)
    try:
        subprocess.check_call([
            "tox", "-e", "wheel",
        ], env={
            **os.environ,
            "VERSION": get_version(True),
        })
    finally:
        set_version(False)


@cli.command("bdist")
def make_bdist():
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

                    # Overwrite mitmproxy/version.py to include commit info
                    set_version(True)
                    try:
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
                    finally:
                        set_version(False)
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
@click.option("--installer/--no-installer", default=False)
def upload_snapshot(host, port, user, private_key, private_key_password, wheel, bdist, installer):
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
            if installer:
                files.append(installer_name())

            for f in files:
                local_path = join(DIST_DIR, f)
                remote_filename = re.sub(
                    r"{version}(\.dev\d+(-0x[0-9a-f]+)?)?".format(version=get_version()),
                    get_version(True, True),
                    f
                )
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
