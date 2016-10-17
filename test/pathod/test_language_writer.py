import io
from pathod import language
from pathod.language import writer


def test_send_chunk():
    v = b"foobarfoobar"
    for bs in range(1, len(v) + 2):
        s = io.BytesIO()
        writer.send_chunk(s, v, bs, 0, len(v))
        assert s.getvalue() == v
        for start in range(len(v)):
            for end in range(len(v)):
                s = io.BytesIO()
                writer.send_chunk(s, v, bs, start, end)
                assert s.getvalue() == v[start:end]


def test_write_values_inject():
    tst = b"foo"

    s = io.BytesIO()
    writer.write_values(s, [tst], [(0, "inject", b"aaa")], blocksize=5)
    assert s.getvalue() == b"aaafoo"

    s = io.BytesIO()
    writer.write_values(s, [tst], [(1, "inject", b"aaa")], blocksize=5)
    assert s.getvalue() == b"faaaoo"

    s = io.BytesIO()
    writer.write_values(s, [tst], [(1, "inject", b"aaa")], blocksize=5)
    assert s.getvalue() == b"faaaoo"


def test_write_values_disconnects():
    s = io.BytesIO()
    tst = b"foo" * 100
    writer.write_values(s, [tst], [(0, "disconnect")], blocksize=5)
    assert not s.getvalue()


def test_write_values():
    tst = b"foobarvoing"
    s = io.BytesIO()
    writer.write_values(s, [tst], [])
    assert s.getvalue() == tst

    for bs in range(1, len(tst) + 2):
        for off in range(len(tst)):
            s = io.BytesIO()
            writer.write_values(
                s, [tst], [(off, "disconnect")], blocksize=bs
            )
            assert s.getvalue() == tst[:off]


def test_write_values_pauses():
    tst = "".join(str(i) for i in range(10)).encode()
    for i in range(2, 10):
        s = io.BytesIO()
        writer.write_values(
            s, [tst], [(2, "pause", 0), (1, "pause", 0)], blocksize=i
        )
        assert s.getvalue() == tst

    for i in range(2, 10):
        s = io.BytesIO()
        writer.write_values(s, [tst], [(1, "pause", 0)], blocksize=i)
        assert s.getvalue() == tst

    tst = [tst] * 5
    for i in range(2, 10):
        s = io.BytesIO()
        writer.write_values(s, tst[:], [(1, "pause", 0)], blocksize=i)
        assert s.getvalue() == b"".join(tst)


def test_write_values_after():
    s = io.BytesIO()
    r = next(language.parse_pathod("400:da"))
    language.serve(r, s, {})

    s = io.BytesIO()
    r = next(language.parse_pathod("400:pa,0"))
    language.serve(r, s, {})

    s = io.BytesIO()
    r = next(language.parse_pathod("400:ia,'xx'"))
    language.serve(r, s, {})
    assert s.getvalue().endswith(b'xx')
