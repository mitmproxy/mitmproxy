def responseheaders(context, flow):
    """
    Enables streaming for all responses.
    """
    flow.response.stream = True
