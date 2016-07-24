from __future__ import absolute_import, print_function, division

import urwid

from mitmproxy.console import signals


class Highlight(urwid.AttrMap):

    def __init__(self, t):
        urwid.AttrMap.__init__(
            self,
            urwid.Text(t.text),
            "focusfield",
        )
        self.backup = t


class Searchable(urwid.ListBox):

    def __init__(self, state, contents):
        self.walker = urwid.SimpleFocusListWalker(contents)
        urwid.ListBox.__init__(self, self.walker)
        self.state = state
        self.search_offset = 0
        self.current_highlight = None
        self.search_term = None

    def keypress(self, size, key):
        if key == "/":
            signals.status_prompt.send(
                prompt = "Search for",
                text = "",
                callback = self.set_search
            )
        elif key == "n":
            self.find_next(False)
        elif key == "N":
            self.find_next(True)
        elif key == "g":
            self.set_focus(0)
            self.walker._modified()
        elif key == "G":
            self.set_focus(len(self.walker) - 1)
            self.walker._modified()
        else:
            return super(self.__class__, self).keypress(size, key)

    def set_search(self, text):
        self.state.last_search = text
        self.search_term = text or None
        self.find_next(False)

    def set_highlight(self, offset):
        if self.current_highlight is not None:
            old = self.body[self.current_highlight]
            self.body[self.current_highlight] = old.backup
        if offset is None:
            self.current_highlight = None
        else:
            self.body[offset] = Highlight(self.body[offset])
            self.current_highlight = offset

    def get_text(self, w):
        if isinstance(w, urwid.Text):
            return w.text
        elif isinstance(w, Highlight):
            return w.backup.text
        else:
            return None

    def find_next(self, backwards):
        if not self.search_term:
            if self.state.last_search:
                self.search_term = self.state.last_search
            else:
                self.set_highlight(None)
                return
        # Start search at focus + 1
        if backwards:
            rng = range(len(self.body) - 1, -1, -1)
        else:
            rng = range(1, len(self.body) + 1)
        for i in rng:
            off = (self.focus_position + i) % len(self.body)
            w = self.body[off]
            txt = self.get_text(w)
            if txt and self.search_term in txt:
                self.set_highlight(off)
                self.set_focus(off, coming_from="above")
                self.body._modified()
                return
        else:
            self.set_highlight(None)
            signals.status_message.send(message="Search not found.", expire=1)
