# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(['pathod'],
             binaries=None,
             datas=collect_data_files("pathod"),
             hiddenimports=['_cffi_backend'],
             hookspath=None,
             runtime_hooks=None,
             excludes=None)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pathod',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon='icon.ico' )
