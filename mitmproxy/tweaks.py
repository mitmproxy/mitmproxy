
class Tweaks:

    """
    Quick fix for those who cannot wait until we have fixed #4836. Set to True
    skip header checking. Keep False if you are using mitmproxy in a forensic
    context.
    """
    no_strict_http2_headers = False

tweaks = Tweaks()
