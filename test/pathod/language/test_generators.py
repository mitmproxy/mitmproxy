from pathod.language import generators


def test_randomgenerator():
    g = generators.RandomGenerator("bytes", 100)
    assert repr(g)
    assert g[0]
    assert len(g[0]) == 1
    assert len(g[:10]) == 10
    assert len(g[1:10]) == 9
    assert len(g[:1000]) == 100
    assert len(g[1000:1001]) == 0


def test_filegenerator(tmpdir):
    f = tmpdir.join("foo")
    f.write(b"abcdefghijklmnopqrstuvwxyz" * 1000)
    g = generators.FileGenerator(str(f))
    assert len(g) == 26000
    assert g[0] == b"a"
    assert g[2:7] == b"cdefg"
    assert len(g[1:10]) == 9
    assert len(g[26000:26001]) == 0
    assert repr(g)


def test_transform_generator():
    def trans(offset, data):
        return "a" * len(data)
    g = "one"
    t = generators.TransformGenerator(g, trans)
    assert len(t) == len(g)
    assert t[0] == "a"
    assert t[:] == "a" * len(g)
    assert repr(t)
