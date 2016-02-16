import urwid

from . import select, common, palettes, signals

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
                lambda: self.master.palette == name,
                lambda: self.select(name)
            )

        for i in high:
            options.append(mkopt(i))
        options.append(select.Heading("Low Colour"))
        for i in low:
            options.append(mkopt(i))

        options.extend(
            [
                select.Heading("Options"),
                select.Option(
                    "Transparent",
                    "T",
                    lambda: master.palette_transparent,
                    self.toggle_palette_transparent
                )
            ]
        )

        self.lb = select.Select(options)
        title = urwid.Text("Palettes")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        self._w = urwid.Frame(
            self.lb,
            header = title
        )
        signals.update_settings.connect(self.sig_update_settings)

    def sig_update_settings(self, sender):
        self.lb.walker._modified()

    def select(self, name):
        self.master.set_palette(name)

    def toggle_palette_transparent(self):
        self.master.palette_transparent = not self.master.palette_transparent
        self.master.set_palette(self.master.palette)
        signals.update_settings.send(self)
