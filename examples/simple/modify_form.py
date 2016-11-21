def request(flow):
    if flow.request.urlencoded_form:
        # If there's already a form, one can just add items to the dict:
        flow.request.urlencoded_form["mitmproxy"] = "rocks"
    else:
        # One can also just pass new form data.
        # This sets the proper content type and overrides the body.
        flow.request.urlencoded_form = [
            ("foo", "bar")
        ]
