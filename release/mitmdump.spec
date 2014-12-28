# -*- mode: python -*-

from glob import glob
block_cipher = None

a = Analysis(['./mitmdump'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher,
          )
a.datas = Tree(
  "./libmproxy/onboarding/templates",
  prefix="libmproxy/onboarding/templates"
)
a.datas += Tree(
  "./libmproxy/onboarding/static",
  prefix="libmproxy/onboarding/static"
)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='mitmdump',
          debug=False,
          strip=None,
          upx=True,
          console=True )
