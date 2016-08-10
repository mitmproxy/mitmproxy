from mitmproxy import exceptions
from mitmproxy import filt


class SetHeaders:
    def __init__(self):
        self.lst = []

    def configure(self, options, updated):
        """
            options.setheaders is a tuple of (fpatt, header, value)

            fpatt: String specifying a filter pattern.
            header: Header name.
            value: Header value string
        """
        for fpatt, header, value in options.setheaders:
            cpatt = filt.parse(fpatt)
            if not cpatt:
                raise exceptions.OptionsError(
                    "Invalid setheader filter pattern %s" % fpatt
                )
            self.lst.append((fpatt, header, value, cpatt))

    def run(self, f, hdrs):
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                hdrs.pop(header, None)
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                hdrs.add(header, value)

    def request(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.request.headers)

    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response.headers)
