import cStringIO

from libpathod import language
from libpathod.language import writer


def test_send_chunk():
    v = "foobarfoobar"
    for bs in range(1, len(v) + 2):
        s = cStringIO.StringIO()
        writer.send_chunk(s, v, bs, 0, len(v))
        assert s.getvalue() == v
        for start in range(len(v)):
            for end in range(len(v)):
                s = cStringIO.StringIO()
                writer.send_chunk(s, v, bs, start, end)
                assert s.getvalue() == v[start:end]


def test_write_values_inject():
    tst = "foo"

    s = cStringIO.StringIO()
    writer.write_values(s, [tst], [(0, "inject", "aaa")], blocksize=5)
    assert s.getvalue() == "aaafoo"

    s = cStringIO.StringIO()
    writer.write_values(s, [tst], [(1, "inject", "aaa")], blocksize=5)
    assert s.getvalue() == "faaaoo"

    s = cStringIO.StringIO()
    writer.write_values(s, [tst], [(1, "inject", "aaa")], blocksize=5)
    assert s.getvalue() == "faaaoo"


def test_write_values_disconnects():
    s = cStringIO.StringIO()
    tst = "foo" * 100
    writer.write_values(s, [tst], [(0, "disconnect")], blocksize=5)
    assert not s.getvalue()


def test_write_values():
    tst = "foobarvoing"
    s = cStringIO.StringIO()
    writer.write_values(s, [tst], [])
    assert s.getvalue() == tst

    for bs in range(1, len(tst) + 2):
        for off in range(len(tst)):
            s = cStringIO.StringIO()
            writer.write_values(
                s, [tst], [(off, "disconnect")], blocksize=bs
            )
            assert s.getvalue() == tst[:off]


def test_write_values_pauses():
    tst = "".join(str(i) for i in range(10))
    for i in range(2, 10):
        s = cStringIO.StringIO()
        writer.write_values(
            s, [tst], [(2, "pause", 0), (1, "pause", 0)], blocksize=i
        )
        assert s.getvalue() == tst

    for i in range(2, 10):
        s = cStringIO.StringIO()
        writer.write_values(s, [tst], [(1, "pause", 0)], blocksize=i)
        assert s.getvalue() == tst

    tst = ["".join(str(i) for i in range(10))] * 5
    for i in range(2, 10):
        s = cStringIO.StringIO()
        writer.write_values(s, tst[:], [(1, "pause", 0)], blocksize=i)
        assert s.getvalue() == "".join(tst)


def test_write_values_after():
    s = cStringIO.StringIO()
    r = language.parse_pathod("400:da")
    language.serve(r, s, {})

    s = cStringIO.StringIO()
    r = language.parse_pathod("400:pa,0")
    language.serve(r, s, {})

    s = cStringIO.StringIO()
    r = language.parse_pathod("400:ia,'xx'")
    language.serve(r, s, {})
    assert s.getvalue().endswith('xx')
