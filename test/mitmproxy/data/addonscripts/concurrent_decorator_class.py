import time
from mitmproxy.script import concurrent


class ConcurrentClass:

    @concurrent
    def request(self, flow):
        time.sleep(0.1)


addons = [ConcurrentClass()]
