from mitmproxy.net.dns import classes


def test_simple():
    assert classes.IN == 1
    assert classes.str(classes.IN) == "IN"
    assert classes.str(0) == "CLASS(0)"
