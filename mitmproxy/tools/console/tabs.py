import urwid


class Tab(urwid.WidgetWrap):

    def __init__(self, offset, content, attr, onclick):
        """
            onclick is called on click with the tab offset as argument
        """
        p = urwid.Text(content, align="center")
        p = urwid.Padding(p, align="center", width=("relative", 100))
        p = urwid.AttrWrap(p, attr)
        urwid.WidgetWrap.__init__(self, p)
        self.offset = offset
        self.onclick = onclick

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            self.onclick(self.offset)
            return True


class Tabs(urwid.WidgetWrap):

    def __init__(self, tabs, tab_offset=0):
        super().__init__("")
        self.tab_offset = tab_offset
        self.tabs = tabs
        self.show()

    def change_tab(self, offset):
        self.tab_offset = offset
        self.show()

    def keypress(self, size, key):
        n = len(self.tabs)
        if key in ["tab", "l"]:
            self.change_tab((self.tab_offset + 1) % n)
        elif key == "h":
            self.change_tab((self.tab_offset - 1) % n)
        return self._w.keypress(size, key)

    def show(self):
        headers = []
        for i in range(len(self.tabs)):
            txt = self.tabs[i][0]()
            if i == self.tab_offset:
                headers.append(
                    Tab(
                        i,
                        txt,
                        "heading",
                        self.change_tab
                    )
                )
            else:
                headers.append(
                    Tab(
                        i,
                        txt,
                        "heading_inactive",
                        self.change_tab
                    )
                )
        headers = urwid.Columns(headers, dividechars=1)
        self._w = urwid.Frame(
            body = self.tabs[self.tab_offset][1](),
            header = headers
        )
        self._w.set_focus("body")
