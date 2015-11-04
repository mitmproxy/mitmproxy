import os
from unittest.case import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")


import libmproxy.console.common as common
import tutils


def test_format_flow():
    f = tutils.tflow(resp=True)
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)
