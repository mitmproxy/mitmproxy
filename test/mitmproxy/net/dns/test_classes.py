from mitmproxy.net.dns import classes


def test_to_str():
    assert classes.to_str(classes.IN) == "IN"
    assert classes.to_str(0) == "CLASS(0)"


def test_from_str():
    assert classes.from_str("IN") == classes.IN
    assert classes.from_str("CLASS(0)") == 0
