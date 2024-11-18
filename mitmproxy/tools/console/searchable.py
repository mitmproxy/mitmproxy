import logging
from dataclasses import dataclass
from typing import Optional

import urwid

from mitmproxy.tools.console import signals


class Highlight(urwid.AttrMap):
    def __init__(self, t):
        urwid.AttrMap.__init__(
            self,
            urwid.Text(t.text),
            "focusfield",
        )
        self.backup = t


@dataclass
class SearchableContext:
    current_highlight: Optional[int] = None
    search_term: Optional[str] = None
    last_search: Optional[str] = None
    focus: int = 0
    queued_search_direction: Optional[bool] = None


class Searchable(urwid.ListBox):
    context: SearchableContext

    def __init__(self, contents, context: Optional[SearchableContext] = None):
        self.walker = urwid.SimpleFocusListWalker(contents)
        urwid.ListBox.__init__(self, self.walker)
        self.context = context if context is not None else SearchableContext()
        self.last_search = None
        if self.context.current_highlight is not None:
            if len(self.body) > self.context.current_highlight:
                self.body[self.context.current_highlight] = Highlight(
                    self.body[self.context.current_highlight]
                )
            else:
                self.context.current_highlight = None
        try:
            self.set_focus(self.context.focus)
        except IndexError:
            self.context.focus = 0

        if self.context.queued_search_direction is not None:
            self.find_next(self.context.queued_search_direction)
        self.walker._modified()

    def keypress(self, size, key: str):
        result: Optional[str] = None
        if key == "/":
            signals.status_prompt.send(
                prompt="Search for", text="", callback=self.set_search
            )
        elif key == "n":
            self.find_next(False)
        elif key == "N":
            self.find_next(True)
        elif key == "m_start":
            self.set_focus(0)
            self.context.focus = 0
            self.walker._modified()
        elif key == "m_end":
            self.set_focus(len(self.walker) - 1)
            self.context.focus = len(self.walker) - 1
            self.walker._modified()
        else:
            result = super().keypress(size, key)

        try:
            self.context.focus = self.focus_position
        except IndexError:
            self.context.focus = 0

        return result

    def set_search(self, text):
        self.context.last_search = text
        self.context.search_term = text or None
        self.find_next(False)

    def set_highlight(self, offset):
        if self.context.current_highlight is not None:
            old = self.body[self.context.current_highlight]
            self.body[self.context.current_highlight] = old.backup
        if offset is None:
            self.context.current_highlight = None
        else:
            self.body[offset] = Highlight(self.body[offset])
            self.context.current_highlight = offset

    def get_text(self, w):
        if isinstance(w, urwid.Text):
            return w.text
        elif isinstance(w, Highlight):
            return w.backup.text
        else:
            return None

    def on_not_found(self):
        """Called when search process reached end of loaded document and will check
        from the beginning or end (in case it is backward search).
        It is intended to be overloaded, return True if search should continue, False otherwise
        """
        return True

    def find_next(self, backwards: bool):
        logging.info(
            f"find_next called {self.context.search_term} {self.context.last_search}"
        )
        if not self.context.search_term:
            if self.context.last_search:
                self.context.search_term = self.context.last_search
            else:
                self.set_highlight(None)
                return
        self.context.queued_search_direction = backwards
        # Start search at focus + 1
        if backwards:
            rng = range(len(self.body) - 1, -1, -1)
        else:
            rng = range(1, len(self.body) + 1)
        for i in rng:
            off = (self.focus_position + i) % len(self.body)
            if off == 0:
                if not self.on_not_found():
                    return
            w = self.body[off]
            txt = self.get_text(w)
            if txt and self.context.search_term in txt:
                self.set_highlight(off)
                self.set_focus(off, coming_from="above")
                self.context.focus = off
                self.body._modified()
                break
        else:
            self.set_highlight(None)
            signals.status_message.send(message="Search not found.", expire=1)

        self.context.queued_search_direction = None
