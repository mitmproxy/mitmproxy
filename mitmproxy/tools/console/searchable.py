import urwid

from mitmproxy.tools.console import signals

Markup = list[tuple[str | None, str]]


def highlight_matches(
    text: str, attrs: list[tuple[str | None, int]], search_term: str
) -> Markup | None:
    """
    Rebuild the markup of a line so that every occurrence of search_term uses the
    "focusfield" attribute while the rest keeps its original syntax highlighting.

    Returns None if the line does not contain the search term.
    """
    if not search_term:
        return None

    matches = []
    pos = text.find(search_term)
    while pos != -1:
        matches.append((pos, pos + len(search_term)))
        pos = text.find(search_term, pos + len(search_term))
    if not matches:
        return None

    runs = []
    pos = 0
    for attr, length in attrs:
        runs.append((pos, pos + length, attr))
        pos += length
    if pos < len(text):
        runs.append((pos, len(text), None))

    boundaries = {0, len(text)}
    for start, end in matches:
        boundaries.update((start, end))
    for start, end, _ in runs:
        boundaries.update((start, end))

    markup: Markup = []
    cuts = sorted(b for b in boundaries if 0 <= b <= len(text))
    for start, end in zip(cuts, cuts[1:]):
        if start == end:
            continue
        if any(m_start <= start < m_end for m_start, m_end in matches):
            attr = "focusfield"
        else:
            attr = next(
                (a for r_start, r_end, a in runs if r_start <= start < r_end), None
            )
        if markup and markup[-1][0] == attr:
            markup[-1] = (attr, markup[-1][1] + text[start:end])
        else:
            markup.append((attr, text[start:end]))
    return markup


class Highlight(urwid.AttrMap):
    def __init__(self, t, search_term: str | None = None):
        text, attrs = t.get_text()
        markup = highlight_matches(text, attrs, search_term or "")
        if markup is None:
            # No known match position, fall back to highlighting the entire line.
            urwid.AttrMap.__init__(self, urwid.Text(text), "focusfield")
        else:
            urwid.AttrMap.__init__(self, urwid.Text(markup), None)
        self.backup = t


class SearchState:
    """
    The last search term is shared between all Searchable instances: the flow view
    rebuilds its widgets whenever the focused flow changes, and an instance-local
    term would make `n`/`N` stop working after any such rebuild.
    """

    last_search: str | None = None


class Searchable(urwid.ListBox):
    def __init__(self, contents):
        self.walker = urwid.SimpleFocusListWalker(contents)
        urwid.ListBox.__init__(self, self.walker)
        self.search_offset = 0
        self.current_highlight = None
        self.search_term = None

    @property
    def last_search(self) -> str | None:
        return SearchState.last_search

    @last_search.setter
    def last_search(self, text: str | None) -> None:
        SearchState.last_search = text

    def keypress(self, size, key: str):
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
            self.walker._modified()
        elif key == "m_end":
            self.set_focus(len(self.walker) - 1)
            self.walker._modified()
        else:
            return super().keypress(size, key)

    def set_search(self, text):
        self.last_search = text
        self.search_term = text or None
        self.find_next(False)

    def set_highlight(self, offset):
        if self.current_highlight is not None:
            old = self.body[self.current_highlight]
            self.body[self.current_highlight] = old.backup
        if offset is None:
            self.current_highlight = None
        else:
            self.body[offset] = Highlight(self.body[offset], self.search_term)
            self.current_highlight = offset

    def get_text(self, w):
        if isinstance(w, urwid.Text):
            return w.text
        elif isinstance(w, Highlight):
            return w.backup.text
        else:
            return None

    def find_next(self, backwards: bool):
        if not self.search_term:
            if self.last_search:
                self.search_term = self.last_search
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
