from libmproxy import encoding


def test_identity():
    assert "string" == encoding.decode("identity", "string")
    assert "string" == encoding.encode("identity", "string")
    assert not encoding.encode("nonexistent", "string")
    assert None == encoding.decode("nonexistent encoding", "string")


def test_gzip():
    assert "string" == encoding.decode(
        "gzip",
        encoding.encode(
            "gzip",
            "string"))
    assert None == encoding.decode("gzip", "bogus")


def test_deflate():
    assert "string" == encoding.decode(
        "deflate",
        encoding.encode(
            "deflate",
            "string"))
    assert "string" == encoding.decode(
        "deflate",
        encoding.encode(
            "deflate",
            "string")[
            2:-
            4])
    assert None == encoding.decode("deflate", "bogus")
