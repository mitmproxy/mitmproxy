from netlib import encoding


def test_identity():
    assert b"string" == encoding.decode("identity", b"string")
    assert b"string" == encoding.encode("identity", b"string")
    assert not encoding.encode("nonexistent", b"string")
    assert not encoding.decode("nonexistent encoding", b"string")


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
