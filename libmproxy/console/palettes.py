
# Low-color themes should ONLY use the standard foreground and background
# colours listed here:
#
# http://urwid.org/manual/displayattributes.html
#



class Palette:
    _fields = [
        'body', 'foot', 'title', 'editline',

        # Status bar & heading
        'heading', 'heading_key', 'heading_inactive',

        # Help
        'key', 'head', 'text',

        # List and Connections
        'method', 'focus',
        'code_200', 'code_300', 'code_400', 'code_500', 'code_other',
        'error',
        'header', 'highlight', 'intercept', 'replay', 'ack',

        # Hex view
        'offset',

        # Grid Editor
        'focusfield', 'focusfield_error', 'field_error', 'editfield',
    ]
    high = None

    def palette(self):
        l = []
        for i in self._fields:
            v = [i]
            v.extend(self.low[i])
            if self.high and i in self.high:
                v.append(None)
                v.extend(self.high[i])
            l.append(tuple(v))
        return l


class LowDark(Palette):
    """
        Low-color dark background
    """
    low = dict(
        body = ('black', 'dark cyan'),
        foot = ('light gray', 'default'),
        title = ('white,bold', 'default'),
        editline = ('white', 'default'),

        # Status bar & heading
        heading = ('light gray', 'dark blue'),
        heading_key = ('light cyan', 'dark blue'),
        heading_inactive = ('white', 'dark gray'),

        # Help
        key = ('light cyan', 'default'),
        head = ('white,bold', 'default'),
        text = ('light gray', 'default'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('yellow', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('light red', 'default'),
        code_500 = ('light red', 'default'),
        code_other = ('dark red', 'default'),

        error = ('light red', 'default'),

        header = ('dark cyan', 'default'),
        highlight = ('white,bold', 'default'),
        intercept = ('brown', 'default'),
        replay = ('light green', 'default'),
        ack = ('light red', 'default'),

        # Hex view
        offset = ('dark cyan', 'default'),

        # Grid Editor
        focusfield = ('black', 'light gray'),
        focusfield_error = ('dark red', 'light gray'),
        field_error = ('dark red', 'default'),
        editfield = ('white', 'default'),
    )


class Dark(LowDark):
    high = dict(
        heading_inactive = ('g58', 'g11'),
        intercept = ('#f60', 'default'),
    )


class LowLight(Palette):
    """
        Low-color light background
    """
    low = dict(
        body = ('black', 'dark cyan'),
        foot = ('dark gray', 'default'),
        title = ('dark magenta,bold', 'light blue'),
        editline = ('white', 'default'),

        # Status bar & heading
        heading = ('light gray', 'dark blue'),
        heading_key = ('light cyan', 'dark blue'),
        heading_inactive = ('black', 'light gray'),

        # Help
        key = ('dark blue,bold', 'default'),
        head = ('black,bold', 'default'),
        text = ('dark gray', 'default'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('black', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('dark red', 'default'),
        code_500 = ('dark red', 'default'),
        code_other = ('light red', 'default'),

        error = ('light red', 'default'),

        header = ('dark blue', 'default'),
        highlight = ('black,bold', 'default'),
        intercept = ('brown', 'default'),
        replay = ('dark green', 'default'),
        ack = ('dark red', 'default'),

        # Hex view
        offset = ('dark blue', 'default'),

        # Grid Editor
        focusfield = ('black', 'light gray'),
        focusfield_error = ('dark red', 'light gray'),
        field_error = ('dark red', 'black'),
        editfield = ('black', 'default'),
    )


class Light(LowLight):
    high = dict(
        heading = ('g99', '#08f'),
        heading_key = ('#0ff,bold', '#08f'),
        heading_inactive = ('g35', 'g85'),
        replay = ('#0a0,bold', 'default'),
    )


class SolarizedLight(LowLight):
    high = dict(
        body = ('dark cyan', 'default'),
        food = ('dark gray', 'default'),
        title = ('white,bold', 'light cyan'),
        editline = ('white', 'default'),

        # Status bar & heading
        heading = ('light cyan', 'light gray'),
        heading_key = ('dark blue', 'white'),
        heading_inactive = ('white', 'light gray'),

        # Help
        key = ('dark blue', 'default',),
        head = ('black,underline', 'default'),
        text = ('light cyan', 'default'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('black', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('dark red', 'default',),
        code_500 = ('dark red', 'default'),
        code_other = ('light red', 'default'),

        error = ('light red', 'default'),

        header = ('light cyan', 'default'),
        highlight = ('black,bold', 'default'),
        intercept = ('brown', 'default',),
        replay = ('dark green', 'default',),
        ack = ('dark red', 'default'),

        # Hex view
        offset = ('light cyan', 'default'),

        # Grid Editor
        focusfield = ('black', 'light gray'),
        focusfield_error = ('dark red', 'light gray'),
        field_error = ('dark red', 'black'),
        editfield = ('white', 'light cyan'),
    )

class SolarizedDark(LowDark):
    high = dict(
        body = ('dark cyan', 'default'),
        foot = ('dark gray', 'default'),
        title = ('white,bold', 'default',),
        editline = ('white', 'default',),

        # Status bar & heading
        heading = ('light gray', 'light cyan',),
        heading_key = ('dark blue', 'white',),
        heading_inactive = ('light cyan', 'light gray',),

        # Help
        key = ('dark blue', 'default',),
        head = ('white,underline', 'default'),
        text = ('light cyan', 'default'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('white', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('dark red', 'default',),
        code_500 = ('dark red', 'default'),
        code_other = ('light red', 'default'),

        error = ('light red', 'default'),

        header = ('yellow', 'default'),
        highlight = ('white', 'default'),
        intercept = ('brown', 'default',),
        replay = ('dark green', 'default',),
        ack = ('dark red', 'default'),

        # Hex view
        offset = ('yellow', 'default'),

        # Grid Editor
        focusfield = ('white', 'light cyan'),
        focusfield_error = ('dark red', 'light gray'),
        field_error = ('dark red', 'black'),
        editfiled = ('black', 'light gray'),
    )


palettes = {
    "lowlight": LowLight(),
    "lowdark": LowDark(),
    "light": Light(),
    "dark": Dark(),
    "solarized_light": SolarizedLight(),
    "solarized_dark": SolarizedDark(),
}
