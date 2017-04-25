class AddHeader:
    def response(self, flow):
        flow.response.headers["newheader"] = "foo"


addons = [AddHeader()]
