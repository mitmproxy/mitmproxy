import struct
import time
from typing import Optional, Iterator

from mitmproxy import tls, connection
from mitmproxy.proxy import layer, commands, context, events
from mitmproxy.proxy.layers import tls as proxy_tls, udp

