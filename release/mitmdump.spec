# -*- mode: python -*-

from glob import glob

a = Analysis(['./mitmdump'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
          )
a.datas = Tree(
  "./libmproxy/onboarding/templates",
  prefix="libmproxy/onboarding/templates"
)
a.datas += Tree(
  "./libmproxy/onboarding/static",
  prefix="libmproxy/onboarding/static"
)
a.datas += Tree(
    "../venv.mitmproxy/lib/python2.7/site-packages/cryptography/hazmat/bindings/openssl/src",
    prefix = "cryptography/hazmat/bindings/openssl/src"
)
pyz = PYZ(a.pure)
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
