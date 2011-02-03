from libmproxy import console, proxy, filt, flow
import utils
import libpry


class uState(libpry.AutoTree):
    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = proxy.ClientConnection(("address", 22))
        c = console.ConsoleState()
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        assert c.lookup(bc)
        assert c.get_focus() == (f, 0)

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()

        bc = proxy.ClientConnection(("address", 22))
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        bc2 = proxy.ClientConnection(("address", 22))
        f2 = flow.Flow(bc2)
        c.add_browserconnect(f2)
        assert c.get_focus() == (f, 1)
        assert c.get_next(0) == (f, 1)
        assert c.get_prev(1) == (f2, 0)
        assert c.get_next(1) == (None, None)

        c.set_focus(0)
        assert c.get_focus() == (f2, 0)
        c.set_focus(-1)
        assert c.get_focus() == (f2, 0)

        c.delete_flow(f2)
        assert c.get_focus() == (f, 0)
        c.delete_flow(f)
        assert c.get_focus() == (None, None)

    def _add_request(self, state):
        f = utils.tflow()
        state.add_browserconnect(f)
        q = utils.treq(f.client_conn)
        state.add_request(q)
        return f

    def _add_response(self, state):
        f = self._add_request(state)
        r = utils.tresp(f.request)
        state.add_response(r)

    def test_add_request(self):
        c = console.ConsoleState()
        f = utils.tflow()
        c.add_browserconnect(f)
        q = utils.treq(f.client_conn)
        c.focus = None
        assert c.add_request(q)

    def test_add_response(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        r = utils.tresp(f.request)
        c.focus = None
        c.add_response(r)

    def test_focus_view(self):
        c = console.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 3
        assert c.focus == 2


class uformat_keyvals(libpry.AutoTree):
    def test_simple(self):
        assert console.format_keyvals(
            [
                ("aa", "bb"),
                None,
                ("cc", "dd"),
            ]
        )


class uformat_flow(libpry.AutoTree):
    def test_simple(self):
        f = utils.tflow()
        assert ('focus', '>> ') not in console.format_flow(f, False)
        assert ('focus', '>> ') in console.format_flow(f, True)

        assert ('focus', '>> ') not in console.format_flow(f, False, True)
        assert ('focus', '>> ') in console.format_flow(f, True, True)

        f.response = utils.tresp()
        f.request = f.response.request
        f.backup()

        assert ('method', '[edited] ') in console.format_flow(f, True)
        assert ('method', '[edited] ') in console.format_flow(f, True, True)
        f.client_conn = proxy.ClientConnection(None)
        assert ('method', '[replay] ') in console.format_flow(f, True)
        assert ('method', '[replay] ') in console.format_flow(f, True, True)


class uPathCompleter(libpry.AutoTree):
    def test_lookup_construction(self):
        c = console._PathCompleter()
        assert c.complete("/tm") == "/tmp/"
        c.reset()

        assert c.complete("./completion/a") == "./completion/aaa"
        c.reset()
        assert c.complete("./completion/aaa") == "./completion/aaa"
        assert c.complete("./completion/aaa") == "./completion/aab"


    def test_completion(self):
        c = console._PathCompleter(True)
        c.reset()
        c.lookup = [
            ("a", "x/a"),
            ("aa", "x/aa"),
        ]
        assert c.complete("a") == "a"
        assert c.final == "x/a"
        assert c.complete("a") == "aa"
        assert c.complete("a") == "a"

        c = console._PathCompleter(True)
        r = c.complete("l")
        assert c.final.endswith(r)

        c.reset()
        assert c.complete("/nonexistent") == "/nonexistent"
        assert c.final == "/nonexistent"
        c.reset()
        assert c.complete("~") != "~"

        c.reset()
        s = "thisisatotallynonexistantpathforsure"
        assert c.complete(s) == s
        assert c.final == s




tests = [
    uformat_keyvals(),
    uformat_flow(),
    uState(), 
    uPathCompleter()
]
