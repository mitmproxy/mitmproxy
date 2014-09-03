
def request(context, flow):
    if "application/x-www-form-urlencoded" in flow.request.headers["content-type"]:
        frm = flow.request.form_urlencoded
        frm["mitmproxy"] = ["rocks"]
        flow.request.form_urlencoded = frm


