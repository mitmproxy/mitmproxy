from netlib import odict
import tutils


class TestODict:
    def setUp(self):
        self.od = odict.ODict()

    def test_str_err(self):
        h = odict.ODict()
        tutils.raises(ValueError, h.__setitem__, "key", "foo")

    def test_dictToHeader1(self):
        self.od.add("one", "uno")
        self.od.add("two", "due")
        self.od.add("two", "tre")
        expected = [
            "one: uno\r\n",
            "two: due\r\n",
            "two: tre\r\n",
            "\r\n"
        ]
        out = repr(self.od)
        for i in expected:
            assert out.find(i) >= 0

    def test_dictToHeader2(self):
        self.od["one"] = ["uno"]
        expected1 = "one: uno\r\n"
        expected2 = "\r\n"
        out = repr(self.od)
        assert out.find(expected1) >= 0
        assert out.find(expected2) >= 0

    def test_match_re(self):
        h = odict.ODict()
        h.add("one", "uno")
        h.add("two", "due")
        h.add("two", "tre")
        assert h.match_re("uno")
        assert h.match_re("two: due")
        assert not h.match_re("nonono")

    def test_getset_state(self):
        self.od.add("foo", 1)
        self.od.add("foo", 2)
        self.od.add("bar", 3)
        state = self.od._get_state()
        nd = odict.ODict._from_state(state)
        assert nd == self.od

    def test_in_any(self):
        self.od["one"] = ["atwoa", "athreea"]
        assert self.od.in_any("one", "two")
        assert self.od.in_any("one", "three")
        assert not self.od.in_any("one", "four")
        assert not self.od.in_any("nonexistent", "foo")
        assert not self.od.in_any("one", "TWO")
        assert self.od.in_any("one", "TWO", True)

    def test_iter(self):
        assert not [i for i in self.od]
        self.od.add("foo", 1)
        assert [i for i in self.od]

    def test_keys(self):
        assert not self.od.keys()
        self.od.add("foo", 1)
        assert self.od.keys() == ["foo"]
        self.od.add("foo", 2)
        assert self.od.keys() == ["foo"]
        self.od.add("bar", 2)
        assert len(self.od.keys()) == 2

    def test_copy(self):
        self.od.add("foo", 1)
        self.od.add("foo", 2)
        self.od.add("bar", 3)
        assert self.od == self.od.copy()

    def test_del(self):
        self.od.add("foo", 1)
        self.od.add("Foo", 2)
        self.od.add("bar", 3)
        del self.od["foo"]
        assert len(self.od.lst) == 2

    def test_replace(self):
        self.od.add("one", "two")
        self.od.add("two", "one")
        assert self.od.replace("one", "vun") == 2
        assert self.od.lst == [
            ["vun", "two"],
            ["two", "vun"],
        ]

    def test_get(self):
        self.od.add("one", "two")
        assert self.od.get("one") == ["two"]
        assert self.od.get("two") == None

    def test_get_first(self):
        self.od.add("one", "two")
        self.od.add("one", "three")
        assert self.od.get_first("one") == "two"
        assert self.od.get_first("two") == None


class TestODictCaseless:
    def setUp(self):
        self.od = odict.ODictCaseless()

    def test_override(self):
        o = odict.ODictCaseless()
        o.add('T', 'application/x-www-form-urlencoded; charset=UTF-8')
        o["T"] = ["foo"]
        assert o["T"] == ["foo"]

    def test_case_preservation(self):
        self.od["Foo"] = ["1"]
        assert "foo" in self.od
        assert self.od.items()[0][0] == "Foo"
        assert self.od.get("foo") == ["1"]
        assert self.od.get("foo", [""]) == ["1"]
        assert self.od.get("Foo", [""]) == ["1"]
        assert self.od.get("xx", "yy") == "yy"

    def test_del(self):
        self.od.add("foo", 1)
        self.od.add("Foo", 2)
        self.od.add("bar", 3)
        del self.od["foo"]
        assert len(self.od) == 1

    def test_keys(self):
        assert not self.od.keys()
        self.od.add("foo", 1)
        assert self.od.keys() == ["foo"]
        self.od.add("Foo", 2)
        assert self.od.keys() == ["foo"]
        self.od.add("bar", 2)
        assert len(self.od.keys()) == 2

