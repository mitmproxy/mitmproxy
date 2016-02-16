import os

from pathod.language import generators
import tutils


def test_randomgenerator():
    g = generators.RandomGenerator("bytes", 100)
    assert repr(g)
    assert len(g[:10]) == 10
    assert len(g[1:10]) == 9
    assert len(g[:1000]) == 100
    assert len(g[1000:1001]) == 0
    assert g[0]


def test_filegenerator():
    with tutils.tmpdir() as t:
        path = os.path.join(t, "foo")
        f = open(path, "wb")
        f.write("x" * 10000)
        f.close()
        g = generators.FileGenerator(path)
        assert len(g) == 10000
        assert g[0] == "x"
        assert g[-1] == "x"
        assert g[0:5] == "xxxxx"
        assert repr(g)
        # remove all references to FileGenerator instance to close the file
        # handle.
        del g


def test_transform_generator():
    def trans(offset, data):
        return "a" * len(data)
    g = "one"
    t = generators.TransformGenerator(g, trans)
    assert len(t) == len(g)
    assert t[0] == "a"
    assert t[:] == "a" * len(g)
    assert repr(t)
