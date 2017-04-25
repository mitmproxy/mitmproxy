import time
from mitmproxy.script import concurrent


class ConcurrentClass:

    @concurrent
    def request(flow):
        time.sleep(0.1)


addons = [ConcurrentClass()]
