class AddHeader:
    def response(self, flow):
        flow.response.headers["newheader"] = "foo"


def load(opts):
    return AddHeader()
