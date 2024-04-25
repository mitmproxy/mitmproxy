# -*- mode: python ; coding: utf-8 -*-

for tool in ["mitmproxy", "mitmdump", "mitmweb"]:
    excludes = []
    if tool != "mitmweb":
        excludes.append("mitmproxy.tools.web")
    if tool != "mitmproxy":
        excludes.append("mitmproxy.tools.console")

    options = []
    if tool == "mitmdump":
        # https://github.com/mitmproxy/mitmproxy/issues/6757
        options.append(("unbuffered", None, "OPTION"))

    a = Analysis(
        [tool],
        excludes=excludes,
    )
    pyz = PYZ(a.pure, a.zipped_data)

    EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        options,
        name=tool,
        console=True,
        icon="icon.ico",
    )
