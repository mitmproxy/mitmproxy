import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

from netlib import encoding

import libmproxy.console.common as common
from libmproxy import utils, flow
import tutils


def test_format_flow():
    f = tutils.tflow(resp=True)
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)
