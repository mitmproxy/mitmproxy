from netlib import encoding


def test_identity():
    assert "string" == encoding.decode("identity", "string")
    assert "string" == encoding.encode("identity", "string")
    assert not encoding.encode("nonexistent", "string")
    assert None == encoding.decode("nonexistent encoding", "string")


def test_gzip():
    assert b"string" == encoding.decode(
        "gzip",
        encoding.encode(
            "gzip",
            b"string"
        )
    )
    assert encoding.decode("gzip", b"bogus") is None


def test_deflate():
    assert b"string" == encoding.decode(
        "deflate",
        encoding.encode(
            "deflate",
            b"string"
        )
    )
    assert b"string" == encoding.decode(
        "deflate",
        encoding.encode(
            "deflate",
            b"string"
        )[2:-4]
    )
    assert encoding.decode("deflate", b"bogus") is None
