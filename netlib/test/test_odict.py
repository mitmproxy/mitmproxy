from netlib import odict, tutils


class TestODict(object):

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
        od = odict.ODict()
        od.add("foo", 1)
        od.add("foo", 2)
        od.add("bar", 3)
        state = od.get_state()
        nd = odict.ODict.from_state(state)
        assert nd == od
        b = odict.ODict()
        b.set_state(state)
        assert b == od

    def test_in_any(self):
        od = odict.ODict()
        od["one"] = ["atwoa", "athreea"]
        assert od.in_any("one", "two")
        assert od.in_any("one", "three")
        assert not od.in_any("one", "four")
        assert not od.in_any("nonexistent", "foo")
        assert not od.in_any("one", "TWO")
        assert od.in_any("one", "TWO", True)

    def test_iter(self):
        od = odict.ODict()
        assert not [i for i in od]
        od.add("foo", 1)
        assert [i for i in od]

    def test_keys(self):
        od = odict.ODict()
        assert not od.keys()
        od.add("foo", 1)
        assert od.keys() == ["foo"]
        od.add("foo", 2)
        assert od.keys() == ["foo"]
        od.add("bar", 2)
        assert len(od.keys()) == 2

    def test_copy(self):
        od = odict.ODict()
        od.add("foo", 1)
        od.add("foo", 2)
        od.add("bar", 3)
        assert od == od.copy()
        assert not od != od.copy()

    def test_del(self):
        od = odict.ODict()
        od.add("foo", 1)
        od.add("Foo", 2)
        od.add("bar", 3)
        del od["foo"]
        assert len(od.lst) == 2

    def test_replace(self):
        od = odict.ODict()
        od.add("one", "two")
        od.add("two", "one")
        assert od.replace("one", "vun") == 2
        assert od.lst == [
            ["vun", "two"],
            ["two", "vun"],
        ]

    def test_get(self):
        od = odict.ODict()
        od.add("one", "two")
        assert od.get("one") == ["two"]
        assert od.get("two") is None

    def test_get_first(self):
        od = odict.ODict()
        od.add("one", "two")
        od.add("one", "three")
        assert od.get_first("one") == "two"
        assert od.get_first("two") is None

    def test_extend(self):
        a = odict.ODict([["a", "b"], ["c", "d"]])
        b = odict.ODict([["a", "b"], ["e", "f"]])
        a.extend(b)
        assert len(a) == 4
        assert a["a"] == ["b", "b"]


class TestODictCaseless(object):

    def test_override(self):
        o = odict.ODictCaseless()
        o.add('T', 'application/x-www-form-urlencoded; charset=UTF-8')
        o["T"] = ["foo"]
        assert o["T"] == ["foo"]

    def test_case_preservation(self):
        od = odict.ODictCaseless()
        od["Foo"] = ["1"]
        assert "foo" in od
        assert od.items()[0][0] == "Foo"
        assert od.get("foo") == ["1"]
        assert od.get("foo", [""]) == ["1"]
        assert od.get("Foo", [""]) == ["1"]
        assert od.get("xx", "yy") == "yy"

    def test_del(self):
        od = odict.ODictCaseless()
        od.add("foo", 1)
        od.add("Foo", 2)
        od.add("bar", 3)
        del od["foo"]
        assert len(od) == 1

    def test_keys(self):
        od = odict.ODictCaseless()
        assert not od.keys()
        od.add("foo", 1)
        assert od.keys() == ["foo"]
        od.add("Foo", 2)
        assert od.keys() == ["foo"]
        od.add("bar", 2)
        assert len(od.keys()) == 2

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
