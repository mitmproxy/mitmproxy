from pathlib import Path
import platform

from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis

here = Path(r".")
tools = ["mitmproxy", "mitmdump", "mitmweb"]

if platform.system() == "Darwin":
    icon = "icon.icns"
else:
    icon = "icon.ico"

analysis = Analysis(
    tools,
    excludes=["tcl", "tk", "tkinter"],
    pathex=[str(here)],
)

pyz = PYZ(analysis.pure, analysis.zipped_data)
executables = []
for tool in tools:
    executables.append(EXE(
        pyz,
        # analysis.scripts has all runtime hooks and all of our tools.
        # remove the other tools.
        [s for s in analysis.scripts if s[0] not in tools or s[0] == tool],
        [],
        exclude_binaries=True,
        name=tool,
        console=True,
        upx=False,
        icon=icon,
        codesign_identity='Developer ID Application',
        entitlements_file=str(here / "macos-entitlements.plist"),
    ))

coll = COLLECT(
    *executables,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="onedir"
)

if platform.system() == "Darwin":
    from PyInstaller.building.osx import BUNDLE
    app = BUNDLE(
        # hack: add dummy executable that opens the terminal,
        # workaround for https://github.com/pyinstaller/pyinstaller/pull/5419
        [(".mitmproxy-wrapper", str(here / ".mitmproxy-wrapper"), "EXECUTABLE")],
        coll,
        name='mitmproxy.app',
        icon=icon,
        bundle_identifier="org.mitmproxy",
    )
