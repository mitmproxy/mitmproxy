from pathlib import Path

from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.build_main import Analysis

assert SPECPATH == "."

here = Path(r".")
tools = ["mitmproxy", "mitmdump", "mitmweb"]

analysis = Analysis(
    tools,
    excludes=["tcl", "tk", "tkinter"],
    pathex=[str(here)],
    hookspath=[str(here / ".." / "hooks")],
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
        icon='icon.ico'
    ))

COLLECT(
    *executables,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=False,
    name="onedir"
)
