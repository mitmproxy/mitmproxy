from netlib import odict, tutils


class TestODict(object):

    def setUp(self):
        self.od = odict.ODict()

    def test_repr(self):
        h = odict.ODict()
        h["one"] = ["two"]
        assert repr(h)

    def test_str_err(self):
        h = odict.ODict()
        with tutils.raises(ValueError):
            h["key"] = u"foo"
        with tutils.raises(ValueError):
            h["key"] = b"foo"

    def test_getset_state(self):
        self.od.add("foo", 1)
        self.od.add("foo", 2)
        self.od.add("bar", 3)
        state = self.od.get_state()
        nd = odict.ODict.from_state(state)
        assert nd == self.od
        b = odict.ODict()
        b.load_state(state)
        assert b == self.od

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
        assert not self.od != self.od.copy()

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
        assert self.od.get("two") is None

    def test_get_first(self):
        self.od.add("one", "two")
        self.od.add("one", "three")
        assert self.od.get_first("one") == "two"
        assert self.od.get_first("two") is None

    def test_extend(self):
        a = odict.ODict([["a", "b"], ["c", "d"]])
        b = odict.ODict([["a", "b"], ["e", "f"]])
        a.extend(b)
        assert len(a) == 4
        assert a["a"] == ["b", "b"]


class TestODictCaseless(object):

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

    def test_add_order(self):
        od = odict.ODict(
            [
                ["one", "uno"],
                ["two", "due"],
                ["three", "tre"],
            ]
        )
        od["two"] = ["foo", "bar"]
        assert od.lst == [
            ["one", "uno"],
            ["two", "foo"],
            ["three", "tre"],
            ["two", "bar"],
        ]
