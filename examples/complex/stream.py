def responseheaders(flow):
    """
    Enables streaming for all responses.
    This is equivalent to passing `--stream 0` to mitmproxy.
    """
    flow.response.stream = True
