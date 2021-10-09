import os
import socket
import logging

import pytest

from mitmproxy.utils import data


# Silence third-party modules
logging.getLogger("hyper").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("passlib").setLevel(logging.WARNING)
logging.getLogger("tornado").setLevel(logging.WARNING)

pytest_plugins = ('test.full_coverage_plugin',)

skip_windows = pytest.mark.skipif(
    os.name == "nt",
    reason='Skipping due to Windows'
)

skip_not_windows = pytest.mark.skipif(
    os.name != "nt",
    reason='Skipping due to not Windows'
)

try:
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.bind(("::1", 0))
    s.close()
except OSError:
    no_ipv6 = True
else:
    no_ipv6 = False

skip_no_ipv6 = pytest.mark.skipif(
    no_ipv6,
    reason='Host has no IPv6 support'
)


@pytest.fixture()
def tdata():
    return data.Data(__name__)
