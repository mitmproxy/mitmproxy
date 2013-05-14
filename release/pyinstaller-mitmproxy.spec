# -*- mode: python -*-
a = Analysis(['/Users/aldo/git/public/mitmproxy/mitmproxy'],
             hiddenimports=["pyamf"],
             hookspath=None,
             runtime_hooks=None)
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
