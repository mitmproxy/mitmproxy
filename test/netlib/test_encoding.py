from netlib import encoding, tutils


def test_identity():
    assert b"string" == encoding.decode(b"string", "identity")
    assert b"string" == encoding.encode(b"string", "identity")
    with tutils.raises(ValueError):
        encoding.encode(b"string", "nonexistent encoding")


def test_gzip():
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "gzip"
        ),
        "gzip"
    )
    with tutils.raises(ValueError):
        encoding.decode(b"bogus", "gzip")


def test_deflate():
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "deflate"
        ),
        "deflate"
    )
    assert b"string" == encoding.decode(
        encoding.encode(
            b"string",
            "deflate"
        )[2:-4],
        "deflate"
    )
    with tutils.raises(ValueError):
        encoding.decode(b"bogus", "deflate")
