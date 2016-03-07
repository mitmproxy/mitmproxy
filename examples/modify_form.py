def request(context, flow):
    form = flow.request.urlencoded_form
    if form is not None:
        form["mitmproxy"] = ["rocks"]
        flow.request.urlencoded_form = form
