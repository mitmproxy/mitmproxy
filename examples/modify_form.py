from mitmproxy import ctx


def request():
    if ctx.flow.request.urlencoded_form:
        ctx.flow.request.urlencoded_form["mitmproxy"] = "rocks"
    else:
        # This sets the proper content type and overrides the body.
        ctx.flow.request.urlencoded_form = [
            ("foo", "bar")
        ]
