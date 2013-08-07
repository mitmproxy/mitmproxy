
def request(context, flow):
    if "application/x-www-form-urlencoded" in flow.request.headers["content-type"]:
        frm = flow.request.get_form_urlencoded()
        frm["mitmproxy"] = ["rocks"]
        flow.request.set_form_urlencoded(frm)


