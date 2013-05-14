# -*- mode: python -*-

# Copy into the pyinstaller directory
# ./pyinstaller.py --clean -F ./pyinstaller-mitmdump.spec 

a = Analysis(['/Users/aldo/git/public/mitmproxy/mitmdump'],
             hiddenimports=["pyamf"],
             hookspath=None,
             runtime_hooks=None)
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
