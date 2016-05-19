def request(context, flow):
    if flow.request.urlencoded_form is not None:
        flow.request.urlencoded_form["mitmproxy"] = "rocks"
    else:
        # This sets the proper content type and overrides the body.
        flow.request.urlencoded_form = [
            ("foo", "bar")
        ]
