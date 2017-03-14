class AddHeader:
    def response(self, flow):
        flow.response.headers["newheader"] = "foo"


def start(opts):
    return AddHeader()
