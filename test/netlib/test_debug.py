from __future__ import (absolute_import, print_function, division)
from six.moves import cStringIO as StringIO

from netlib import debug


def test_dump_info():
    cs = StringIO()
    debug.dump_info(None, None, file=cs)
    assert cs.getvalue()


def test_sysinfo():
    assert debug.sysinfo()
