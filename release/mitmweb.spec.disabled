# -*- mode: python -*-

from glob import glob

VENV = "../release/venv"

a = Analysis(['../mitmproxy/mitmweb'],
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
  "../mitmproxy/libmproxy/web/templates",
  prefix="libmproxy/web/templates"
)
a.datas += Tree(
  "../mitmproxy/libmproxy/web/static",
  prefix="libmproxy/web/static"
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
          name='mitmweb',
          debug=False,
          strip=None,
          upx=True,
          console=True )
