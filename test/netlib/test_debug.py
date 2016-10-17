from __future__ import (absolute_import, print_function, division)
import io

from netlib import debug


def test_dump_info():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs, testing=True)
    assert cs.getvalue()


def test_dump_stacks():
    cs = io.StringIO()
    debug.dump_stacks(None, None, file=cs, testing=True)
    assert cs.getvalue()


def test_sysinfo():
    assert debug.sysinfo()


def test_register_info_dumpers():
    debug.register_info_dumpers()
