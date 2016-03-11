# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(['mitmdump'],
             binaries=None,
             datas=collect_data_files("mitmproxy.onboarding"),
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='mitmdump',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon='icon.ico' )
