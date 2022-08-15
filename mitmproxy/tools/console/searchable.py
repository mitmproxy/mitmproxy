import urwid
import re

from mitmproxy.tools.console import signals

class Highlight(urwid.AttrMap):
    def __init__(self, t, search_term, word_offset):
        urwid.AttrMap.__init__(
            self,
            self.highlight_text(t, search_term, word_offset),
            None
        )
        self.backup = t

    def highlight_text(self, text, search_term, word_offset):
        text_array = []
        sum = 0
        prev = 0
        word_end = word_offset + len(search_term)
        offset_found = False
        highlight_style = "heading"
        for attrib in text.attrib:
            sum += attrib[1]
            if not offset_found:
                if sum>=word_offset and sum<word_end:
                    text_array.append((attrib[0],text.text[prev:word_offset]))
                    text_array.append((highlight_style,text.text[word_offset:word_end]))
                    offset_found = True
                if sum>=word_offset and sum>=word_end:
                    text_array.append((attrib[0],text.text[prev:word_offset]))
                    text_array.append((highlight_style,text.text[word_offset:word_end]))
                    text_array.append((attrib[0],text.text[word_end:sum]))
                    word_end = sum
                    offset_found = True
                if sum< word_offset:
                    text_array.append((attrib[0],text.text[prev:attrib[1]]))
                prev = sum
            else:
                if sum>=word_end:
                    text_array.append((attrib[0],text.text[word_end:sum]))
                    word_end = sum

        text = urwid.Text(text_array)
        return text


class Match():
    def __init__(self, word, row_nr, column_nr, offset, is_focused, text):
        self.word = word
        self.row_nr = row_nr
        self.column_nr = column_nr
        self.offset = offset
        self.is_focused = is_focused
        self.text = text

    def set_focus(self):
        self.is_focused = True

    def remove_focus(self):
        self.is_focused = False


class Searchable(urwid.ListBox):
    def __init__(self, contents):
        self.walker = urwid.SimpleFocusListWalker(contents)
        urwid.ListBox.__init__(self, self.walker)
        self.current_highlight = None
        self.search_term = None
        self.last_search = None
        self.is_backward = False
        self.matches = []

    def keypress(self, size, key):
        if key == "/":
            signals.status_prompt.send(
                prompt="Search for", text="", callback=self.set_search
            )
        elif key == "n":
            self.is_backward = False
            self.find_next()
        elif key == "N":
            self.is_backward = True
            self.find_next()
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
        self.find_all_matches()

    def highlight_off(self, match):
        if match.column_nr:
            column_tuple_content = list(self.body[match.row_nr].contents[match.column_nr])
            column_tuple_content[0] = self.body[match.row_nr].contents[match.column_nr][0].backup
            column_tuple_content = tuple(column_tuple_content)
            self.body[match.row_nr].contents[match.column_nr] = column_tuple_content
        else:
            self.body[match.row_nr] = self.body[match.row_nr].backup

    def set_highlight(self, match):
        if match.column_nr:
            column_tuple_content = list(self.body[match.row_nr].contents[match.column_nr])
            column_tuple_content[0] = Highlight(self.body[match.row_nr].contents[match.column_nr][0],self.search_term,match.offset)
            column_tuple_content = tuple(column_tuple_content)
            self.body[match.row_nr].contents[match.column_nr] = column_tuple_content
        else:
            self.body[match.row_nr] = Highlight(self.body[match.row_nr],self.search_term,match.offset)
        self.set_focus(match.row_nr, coming_from="above")
        self.body._modified()

    def append_matches(self, row_nr, text, col_nr = None):
        matches = [m.start() for m in re.finditer(self.search_term, text)]
        for offset in matches:
            self.matches.append(Match(self.search_term, row_nr, col_nr, offset, False, text))

    def find_all_matches(self):
        if len(self.matches) > 0:
            for match in self.matches:
                if match.is_focused:
                    self.highlight_off(match)
        self.matches = []
        for row_nr in range(0, len(self.body)):
            row = self.body[row_nr]
            if isinstance(row, urwid.Columns):
                for col_nr in range(0, len(row.contents)):
                    col = row.contents[col_nr]
                    self.append_matches(row_nr, col[0].text, col_nr)
            if isinstance(row, urwid.Text):
                self.append_matches(row_nr, row.text)

        if len(self.matches) > 0:
            self.matches[0].set_focus()
            self.set_highlight(self.matches[0])
        else:
            signals.status_message.send(message="Search not found.", expire=1)

    def find_next(self):
        for match_nr in range(0, len(self.matches)):
            match = self.matches[match_nr]
            if match.is_focused:
                match.remove_focus()
                self.highlight_off(match)
                if self.is_backward:
                    next_match_nr = (match_nr - 1) % len(self.matches)
                else:
                    next_match_nr = (match_nr + 1) % len(self.matches)

                self.matches[next_match_nr].set_focus()
                self.set_highlight(self.matches[next_match_nr])
                return
