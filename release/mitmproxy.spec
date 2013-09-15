# -*- mode: python -*-
# PyInstaller Spec File

import os
from PyInstaller.build import *

scripts = ['mitmdump', 'mitmproxy-gui']
if not os.name == "nt":
    scripts.append('mitmproxy')

analyses = list(Analysis(scripts=['../dist/%s' % s]) for s in scripts)

#merge_info = []
#for i, a in enumerate(analyses):
#    merge_info.append((a, scripts[i], scripts[i] + '.exe'))
#MERGE(*merge_info)

gui_tree = Tree('../dist/libmproxy/gui', prefix='libmproxy/gui')
scripts_tree = Tree('../dist/scripts', prefix='scripts')

executables = []
for i, a in enumerate(analyses):
    executables += [EXE(PYZ(a.pure),
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              gui_tree,
              scripts_tree,
              name=scripts[i] + '.exe',
              upx=True,
              console=True)]