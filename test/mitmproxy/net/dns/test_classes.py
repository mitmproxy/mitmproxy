from mitmproxy.net.dns import classes


def test_simple():
    assert classes.IN == 1
    assert classes.to_str(classes.IN) == "IN"
    assert classes.to_str(0) == "CLASS(0)"
