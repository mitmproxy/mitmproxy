



def test_resolve():
    v = viewhttp2.ViewHttp2()
    with taddons.context() as tctx:
        assert tctx.command(v.resolve, "@all") == []
        assert tctx.command(v.resolve, "@focus") == []
        assert tctx.command(v.resolve, "@shown") == []
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []
        assert tctx.command(v.resolve, "@unmarked") == []
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@all")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 1
        assert len(tctx.command(v.resolve, "@unmarked")) == 1
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []
        assert len(tctx.command(v.resolve, "@focus")) == 1
        assert len(tctx.command(v.resolve, "@shown")) == 2
        assert len(tctx.command(v.resolve, "@all")) == 2
        assert tctx.command(v.resolve, "@hidden") == []
        assert tctx.command(v.resolve, "@marked") == []

        with pytest.raises(exceptions.CommandError, match="Invalid flow filter"):
            tctx.command(v.resolve, "~")



def test_order():
    v = viewhttp2.ViewHttp2()
    v.set_order("time")
    assert v.get_order() == "time"
    assert [i.request.timestamp_start for i in v] == [4, 3, 2, 1]

    v.set_reversed(False)
    assert [i.request.timestamp_start for i in v] == [1, 2, 3, 4]
    with pytest.raises(exceptions.CommandError):
        v.set_order("not_an_order")
