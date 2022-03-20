import time
from mitmproxy.script import concurrent


class ConcurrentClass:

    @concurrent
    def request(self, flow):
        time.sleep(0.25)

    @concurrent
    async def requestheaders(self, flow):
        time.sleep(0.25)


addons = [ConcurrentClass()]
