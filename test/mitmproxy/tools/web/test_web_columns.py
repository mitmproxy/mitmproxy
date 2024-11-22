from mitmproxy.tools.web.web_columns import AVAILABLE_WEB_COLUMNS


def test_web_columns():
    assert isinstance(AVAILABLE_WEB_COLUMNS, list)
