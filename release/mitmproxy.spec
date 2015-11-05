# -*- mode: python -*-
import os.path
from glob import glob

VENV = "../release/venv"

a = Analysis(['../../mitmproxy/mitmproxy'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
          )
a.datas = Tree(
  "../mitmproxy/libmproxy/onboarding/templates",
  prefix="libmproxy/onboarding/templates"
)
a.datas += Tree(
  "../mitmproxy/libmproxy/onboarding/static",
  prefix="libmproxy/onboarding/static"
)
a.datas += Tree(
    os.path.join(
        VENV,
        "lib/python2.7/site-packages/certifi",
    ),
    prefix = "certifi"
)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='mitmproxy',
          debug=False,
          strip=None,
          upx=True,
          console=True )
