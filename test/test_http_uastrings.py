from netlib import http_uastrings


def test_get_shortcut():
    assert http_uastrings.get_by_shortcut("c")[0] == "chrome"
    assert not http_uastrings.get_by_shortcut("_")

