# -*- mode: python -*-

from glob import glob

VENV = "../release/venv"

a = Analysis(['../pathod/pathoc'],
             hiddenimports=["_cffi_backend"],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
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
          name='pathoc',
          debug=False,
          strip=None,
          upx=True,
          console=True )
