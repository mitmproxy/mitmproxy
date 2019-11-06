def test_http_proxy():
    """Test a simple HTTP GET / request"""


def test_https_proxy_eager():
    """Test a CONNECT request, followed by TLS, followed by a HTTP GET /"""


def test_https_proxy_lazy():
    """Test a CONNECT request, followed by TLS, followed by a HTTP GET /"""


def test_http_to_https():
    """Test a simple HTTP GET request that is being rewritten to HTTPS by an addon."""


def test_http_redirect():
    """Test a simple HTTP GET request that redirected to another host"""


def test_multiple_server_connections():
    """Test multiple requests being rewritten to different targets."""


def test_http_reply_from_proxy():
    """Test a response served by mitmproxy itself."""

def test_disconnect_while_intercept():
    """Test a server disconnect while a request is intercepted."""