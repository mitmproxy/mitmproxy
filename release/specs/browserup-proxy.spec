# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['browserup-proxy'],
             pathex=['/home/kirill/dev/epic/bu/mitmproxy-fork/mitmproxy/release/specs'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['/home/kirill/dev/epic/bu/mitmproxy-fork/mitmproxy/release/hooks'],
             runtime_hooks=[],
             excludes=['mitmproxy.tools.web', 'mitmproxy.tools.console'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='browserup-proxy',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , icon='icon.ico')
