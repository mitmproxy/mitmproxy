from time import sleep


class LatencyResource:

    def addon_path(self):
        return "latency/{latency}"

    def __init__(self, latency_addon):
        self.latency_addon = latency_addon

    def on_put(self, req, resp, latency):
        """Puts (sets) a value for latency
        ---
        description: Sets a value for latency in milliseconds. Default is 0.
        operationId: setAddedLatencyMillis
        parameters:
            - in: path
              name: latency
              type: int
              required: true
        tags:
            - BrowserUpProxy
        responses:
            204:
                description: Success!
        """
        self.latency_addon.latency_ms = int(latency)


class LatencyAddOn:

    def __init__(self):
        self.num = 0
        self.latency_ms = 0

    def get_resources(self):
        return [LatencyResource(self)]

    def response(self, flow):
        if self.latency_ms != 0:
            sleep(self.latency_ms / 1000)


addons = [
    LatencyAddOn()
]
