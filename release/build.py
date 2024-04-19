#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import tarfile
import urllib.request
import warnings
import zipfile
from datetime import datetime
from pathlib import Path

import click
import cryptography.fernet

here = Path(__file__).absolute().parent

TEMP_DIR = here / "build"
DIST_DIR = here / "dist"


@click.group(chain=True)
@click.option("--dirty", is_flag=True)
def cli(dirty):
    if dirty:
        print("Keeping temporary files.")
    else:
        print("Cleaning up temporary files...")
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)

        TEMP_DIR.mkdir()
        DIST_DIR.mkdir()


@cli.command()
def wheel():
    """Build the wheel for PyPI."""
    print("Building wheel...")
    subprocess.check_call(
        [
            "python",
            "-m",
            "build",
            "--outdir",
            DIST_DIR,
        ]
    )
    if os.environ.get("GITHUB_REF", "").startswith("refs/tags/"):
        ver = version()  # assert for tags that the version matches the tag.
    else:
        ver = "*"
    (whl,) = DIST_DIR.glob(f"mitmproxy-{ver}-py3-none-any.whl")
    print(f"Found wheel package: {whl}")
    subprocess.check_call(["tox", "-e", "wheeltest", "--", whl])


class ZipFile2(zipfile.ZipFile):
    # ZipFile and tarfile have slightly different APIs. Let's fix that.
    def add(self, name: str, arcname: str) -> None:
        return self.write(name, arcname)

    def __enter__(self) -> ZipFile2:
        return self

    @property
    def name(self) -> str:
        assert self.filename
        return self.filename


def archive(path: Path) -> tarfile.TarFile | ZipFile2:
    if platform.system() == "Windows":
        return ZipFile2(path.with_name(f"{path.name}.zip"), "w")
    else:
        return tarfile.open(path.with_name(f"{path.name}.tar.gz"), "w:gz")


def version() -> str:
    if ref := os.environ.get("GITHUB_REF", ""):
        if ref.startswith("refs/tags/") and not ref.startswith("refs/tags/v"):
            raise AssertionError(f"Unexpected tag: {ref}")
        return (
            ref.removeprefix("refs/heads/")
            .removeprefix("refs/pull/")
            .removeprefix("refs/tags/v")
            .replace("/", "-")
        )
    else:
        return os.environ.get("BUILD_VERSION", "dev")


def operating_system() -> str:
    match platform.system():
        case "Windows":
            system = "windows"
        case "Linux":
            system = "linux"
        case "Darwin":
            system = "macos"
        case other:
            warnings.warn("Unexpected system.")
            system = other
    match platform.machine():
        case "AMD64" | "x86_64":
            machine = "x86_64"
        case "arm64":
            machine = "arm64"
        case other:
            warnings.warn("Unexpected platform.")
            machine = other
    return f"{system}-{machine}"


def _pyinstaller(specfile: str) -> None:
    print(f"Invoking PyInstaller with {specfile}...")
    subprocess.check_call(
        [
            "pyinstaller",
            "--clean",
            "--workpath",
            TEMP_DIR / "pyinstaller/temp",
            "--distpath",
            TEMP_DIR / "pyinstaller/out",
            specfile,
        ],
        cwd=here / "specs",
    )


@cli.command()
def standalone_binaries():
    """Windows and Linux: Build the standalone binaries generated with PyInstaller"""
    with archive(DIST_DIR / f"mitmproxy-{version()}-{operating_system()}") as f:
        _pyinstaller("standalone.spec")

        _test_binaries(TEMP_DIR / "pyinstaller/out")

        for tool in ["mitmproxy", "mitmdump", "mitmweb"]:
            executable = TEMP_DIR / "pyinstaller/out" / tool
            if platform.system() == "Windows":
                executable = executable.with_suffix(".exe")

            f.add(str(executable), str(executable.name))
    print(f"Packed {f.name!r}.")


@cli.command()
@click.option("--keychain")
@click.option("--team-id")
@click.option("--apple-id")
@click.option("--password")
def macos_app(
    keychain: str | None,
    team_id: str | None,
    apple_id: str | None,
    password: str | None,
) -> None:
    """
    macOS: Build into mitmproxy.app.

    If you do not specify options, notarization is skipped.
    """

    _pyinstaller("onedir.spec")
    _test_binaries(TEMP_DIR / "pyinstaller/out/mitmproxy.app/Contents/MacOS")

    if keychain:
        assert isinstance(team_id, str)
        assert isinstance(apple_id, str)
        assert isinstance(password, str)
        # Notarize the app bundle.
        subprocess.check_call(
            [
                "xcrun",
                "notarytool",
                "store-credentials",
                "AC_PASSWORD",
                *(["--keychain", keychain]),
                *(["--team-id", team_id]),
                *(["--apple-id", apple_id]),
                *(["--password", password]),
            ]
        )
        subprocess.check_call(
            [
                "ditto",
                "-c",
                "-k",
                "--keepParent",
                TEMP_DIR / "pyinstaller/out/mitmproxy.app",
                TEMP_DIR / "notarize.zip",
            ]
        )
        subprocess.check_call(
            [
                "xcrun",
                "notarytool",
                "submit",
                TEMP_DIR / "notarize.zip",
                *(["--keychain", keychain]),
                *(["--keychain-profile", "AC_PASSWORD"]),
                "--wait",
            ]
        )
        # 2023: it's not possible to staple to unix executables.
        # subprocess.check_call([
        #     "xcrun",
        #     "stapler",
        #     "staple",
        #     TEMP_DIR / "pyinstaller/out/mitmproxy.app",
        # ])
    else:
        warnings.warn("Notarization skipped.")

    with archive(DIST_DIR / f"mitmproxy-{version()}-{operating_system()}") as f:
        f.add(str(TEMP_DIR / "pyinstaller/out/mitmproxy.app"), "mitmproxy.app")
    print(f"Packed {f.name!r}.")


def _ensure_pyinstaller_onedir():
    if not (TEMP_DIR / "pyinstaller/out/onedir").exists():
        _pyinstaller("onedir.spec")
        _test_binaries(TEMP_DIR / "pyinstaller/out/onedir")


def _test_binaries(binary_directory: Path) -> None:
    for tool in ["mitmproxy", "mitmdump", "mitmweb"]:
        executable = binary_directory / tool
        if platform.system() == "Windows":
            executable = executable.with_suffix(".exe")

        print(f"> {tool} --version")
        subprocess.check_call([executable, "--version"])

        if tool == "mitmproxy":
            continue  # requires a TTY, which we don't have here.

        print(f"> {tool} -s selftest.py")
        subprocess.check_call([executable, "-s", here / "selftest.py"])


@cli.command()
def msix_installer():
    """Windows: Build the MSIX installer for the Windows Store."""
    _ensure_pyinstaller_onedir()

    shutil.copytree(
        TEMP_DIR / "pyinstaller/out/onedir",
        TEMP_DIR / "msix",
        dirs_exist_ok=True,
    )
    shutil.copytree(here / "windows-installer", TEMP_DIR / "msix", dirs_exist_ok=True)

    manifest = TEMP_DIR / "msix/AppxManifest.xml"
    app_version = version()
    if not re.match(r"\d+\.\d+\.\d+", app_version):
        app_version = (
            datetime.now()
            .strftime("%y%m.%d.%H%M")
            .replace(".0", ".")
            .replace(".0", ".")
            .replace(".0", ".")
        )
    manifest.write_text(manifest.read_text().replace("1.2.3", app_version))

    makeappx_exe = (
        Path(os.environ["ProgramFiles(x86)"])
        / "Windows Kits/10/App Certification Kit/makeappx.exe"
    )
    subprocess.check_call(
        [
            makeappx_exe,
            "pack",
            "/d",
            TEMP_DIR / "msix",
            "/p",
            DIST_DIR / f"mitmproxy-{version()}-installer.msix",
        ],
    )
    assert (DIST_DIR / f"mitmproxy-{version()}-installer.msix").exists()


@cli.command()
def installbuilder_installer():
    """Windows: Build the InstallBuilder installer."""
    _ensure_pyinstaller_onedir()

    IB_VERSION = "23.4.0"
    IB_SETUP_SHA256 = "e4ff212ed962f9e0030d918b8a6e4d6dd8a9adc8bf8bc1833459351ee649eff3"
    IB_DIR = here / "installbuilder"
    IB_SETUP = IB_DIR / "setup" / f"{IB_VERSION}-installer.exe"
    IB_CLI = Path(
        rf"C:\Program Files\InstallBuilder Enterprise {IB_VERSION}\bin\builder-cli.exe"
    )
    IB_LICENSE = IB_DIR / "license.xml"

    if not IB_LICENSE.exists():
        print("Decrypt InstallBuilder license...")
        f = cryptography.fernet.Fernet(os.environ["CI_BUILD_KEY"].encode())
        with (
            open(IB_LICENSE.with_suffix(".xml.enc"), "rb") as infile,
            open(IB_LICENSE, "wb") as outfile,
        ):
            outfile.write(f.decrypt(infile.read()))

    if not IB_CLI.exists():
        if not IB_SETUP.exists():
            url = (
                f"https://github.com/mitmproxy/installbuilder-mirror/releases/download/"
                f"{IB_VERSION}/installbuilder-enterprise-{IB_VERSION}-windows-x64-installer.exe"
            )
            print(f"Downloading InstallBuilder from {url}...")

            def report(block, blocksize, total):
                done = block * blocksize
                if round(100 * done / total) != round(100 * (done - blocksize) / total):
                    print(f"Downloading... {round(100 * done / total)}%")

            tmp = IB_SETUP.with_suffix(".tmp")
            urllib.request.urlretrieve(
                url,
                tmp,
                reporthook=report,
            )
            tmp.rename(IB_SETUP)

        ib_setup_hash = hashlib.sha256()
        with IB_SETUP.open("rb") as fp:
            while True:
                data = fp.read(65_536)
                if not data:
                    break
                ib_setup_hash.update(data)
        if ib_setup_hash.hexdigest() != IB_SETUP_SHA256:  # pragma: no cover
            raise RuntimeError(
                f"InstallBuilder hashes don't match: {ib_setup_hash.hexdigest()}"
            )

        print("Install InstallBuilder...")
        subprocess.run(
            [IB_SETUP, "--mode", "unattended", "--unattendedmodeui", "none"], check=True
        )
        assert IB_CLI.is_file()

    print("Run InstallBuilder...")
    subprocess.check_call(
        [
            IB_CLI,
            "build",
            str(IB_DIR / "mitmproxy.xml"),
            "windows-x64",
            "--license",
            str(IB_LICENSE),
            "--setvars",
            f"project.version={version()}",
            "--verbose",
        ],
        cwd=IB_DIR,
    )
    installer = DIST_DIR / f"mitmproxy-{version()}-windows-x64-installer.exe"
    assert installer.exists()

    # unify filenames
    installer = installer.rename(
        installer.with_name(installer.name.replace("x64", "x86_64"))
    )

    print("Run installer...")
    subprocess.run(
        [installer, "--mode", "unattended", "--unattendedmodeui", "none"], check=True
    )
    _test_binaries(Path(r"C:\Program Files\mitmproxy\bin"))


if __name__ == "__main__":
    cli()
