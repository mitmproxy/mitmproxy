from libmproxy import console, filt, flow
import tutils
import libpry


class uState(libpry.AutoTree):
    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
        f = self._add_request(c)
        assert f.request in c._flow_map
        assert c.get_focus() == (f, 0)

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
        f = self._add_request(c)

        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        f2 = self._add_request(c)
        assert c.get_focus() == (f, 0)
        assert c.get_next(0) == (f2, 1)
        assert c.get_prev(1) == (f, 0)
        assert c.get_next(1) == (None, None)

        c.set_focus(0)
        assert c.get_focus() == (f, 0)
        c.set_focus(-1)
        assert c.get_focus() == (f, 0)
        c.set_focus(2)
        assert c.get_focus() == (f2, 1)

        c.delete_flow(f2)
        assert c.get_focus() == (f, 0)
        c.delete_flow(f)
        assert c.get_focus() == (None, None)

    def _add_request(self, state):
        r = tutils.treq()
        return state.add_request(r)

    def _add_response(self, state):
        f = self._add_request(state)
        r = tutils.tresp(f.request)
        state.add_response(r)

    def test_add_response(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        r = tutils.tresp(f.request)
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
        assert not c.set_limit("~q")
        assert len(c.view) == 3
        assert c.focus == 0


class uformat_keyvals(libpry.AutoTree):
    def test_simple(self):
        assert console.format_keyvals(
            [
                ("aa", "bb"),
                None,
                ("cc", "dd"),
                (None, "dd"),
                (None, "dd"),
            ]
        )


class uformat_flow(libpry.AutoTree):
    def test_simple(self):
        f = tutils.tflow()
        foc = ('focus', '>>')
        assert foc not in console.format_flow(f, False)
        assert foc in console.format_flow(f, True)

        assert foc not in console.format_flow(f, False, True)
        assert foc in console.format_flow(f, True, True)

        f.response = tutils.tresp()
        f.request = f.response.request
        f.backup()

        f.request._set_replay()
        f.response._set_replay()
        assert ('method', '[replay]') in console.format_flow(f, True)
        assert ('method', '[replay]') in console.format_flow(f, True, True)

        f.response.code = 404
        assert ('error', '404') in console.format_flow(f, True, True)
        f.response.headers["content-type"] = ["text/html"]
        assert ('text', ' text/html') in console.format_flow(f, True, True)

        f.response =None
        f.error = flow.Error(f.request, "error")
        assert ('error', 'error') in console.format_flow(f, True, True)



class uPathCompleter(libpry.AutoTree):
    def test_lookup_construction(self):
        c = console._PathCompleter()
        assert c.complete("/tm") == "/tmp/"
        c.reset()

        assert c.complete("./completion/a") == "./completion/aaa"
        assert c.complete("./completion/a") == "./completion/aab"
        c.reset()
        assert c.complete("./completion/aaa") == "./completion/aaa"
        assert c.complete("./completion/aaa") == "./completion/aaa"


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


class uOptions(libpry.AutoTree):
    def test_all(self):
        assert console.Options(kill=True)



tests = [
    uformat_keyvals(),
    uformat_flow(),
    uState(), 
    uPathCompleter(),
    uOptions()
]
