import urwid

from . import select, common, palettes

footer = [
    ('heading_key', "enter/space"), ":select",
]

def _mkhelp():
    text = []
    keys = [
        ("enter/space", "select"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()


class PalettePicker(urwid.WidgetWrap):
    def __init__(self, master):
        self.master = master
        low, high = [], []
        for k, v in palettes.palettes.items():
            if v.high:
                high.append(k)
            else:
                low.append(k)
        high.sort()
        low.sort()

        options = [
            select.Heading("High Colour")
        ]

        def mkopt(name):
            return select.Option(
                i,
                None,
                None,
                lambda: self.select(name)
            )

        for i in high:
            options.append(mkopt(i))
        options.append(select.Heading("Low Colour"))
        for i in low:
            options.append(mkopt(i))

        self.lb = select.Select(options)
        title = urwid.Text("Palettes")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        self._w = urwid.Frame(
            self.lb,
            header = title
        )

    def select(self, name):
        self.master.set_palette(name)
