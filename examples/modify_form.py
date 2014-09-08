
def request(context, flow):
    if "application/x-www-form-urlencoded" in flow.request.headers["content-type"]:
        form = flow.request.get_form_urlencoded()
        form["mitmproxy"] = ["rocks"]
        flow.request.set_form_urlencoded(form)