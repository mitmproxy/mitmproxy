class AddHeader:
    def response(self, flow):
        flow.response.headers["newheader"] = "foo"


def load(l):
    return l.boot_into(AddHeader())
