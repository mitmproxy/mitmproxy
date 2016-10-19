# Low-color themes should ONLY use the standard foreground and background
# colours listed here:
#
# http://urwid.org/manual/displayattributes.html
#


class Palette:
    _fields = [
        'background',
        'title',

        # Status bar & heading
        'heading', 'heading_key', 'heading_inactive',

        # Help
        'key', 'head', 'text',

        # Options
        'option_selected', 'option_active', 'option_active_selected',
        'option_selected_key',

        # List and Connections
        'method', 'focus',
        'code_200', 'code_300', 'code_400', 'code_500', 'code_other',
        'error', "warn",
        'header', 'highlight', 'intercept', 'replay', 'mark',

        # Hex view
        'offset',

        # Grid Editor
        'focusfield', 'focusfield_error', 'field_error', 'editfield',
    ]
    high = None

    def palette(self, transparent):
        l = []
        highback, lowback = None, None
        if not transparent:
            if self.high and self.high.get("background"):
                highback = self.high["background"][1]
            lowback = self.low["background"][1]

        for i in self._fields:
            if transparent and i == "background":
                l.append(["background", "default", "default"])
            else:
                v = [i]
                low = list(self.low[i])
                if lowback and low[1] == "default":
                    low[1] = lowback
                v.extend(low)
                if self.high and i in self.high:
                    v.append(None)
                    high = list(self.high[i])
                    if highback and high[1] == "default":
                        high[1] = highback
                    v.extend(high)
                elif highback and self.low[i][1] == "default":
                    high = [None, low[0], highback]
                    v.extend(high)
                l.append(tuple(v))
        return l


class LowDark(Palette):

    """
        Low-color dark background
    """
    low = dict(
        background = ('white', 'black'),
        title = ('white,bold', 'default'),

        # Status bar & heading
        heading = ('white', 'dark blue'),
        heading_key = ('light cyan', 'dark blue'),
        heading_inactive = ('dark gray', 'light gray'),

        # Help
        key = ('light cyan', 'default'),
        head = ('white,bold', 'default'),
        text = ('light gray', 'default'),

        # Options
        option_selected = ('black', 'light gray'),
        option_selected_key = ('light cyan', 'light gray'),
        option_active = ('light red', 'default'),
        option_active_selected = ('light red', 'light gray'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('yellow', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('light red', 'default'),
        code_500 = ('light red', 'default'),
        code_other = ('dark red', 'default'),

        warn = ('brown', 'default'),
        error = ('light red', 'default'),

        header = ('dark cyan', 'default'),
        highlight = ('white,bold', 'default'),
        intercept = ('brown', 'default'),
        replay = ('light green', 'default'),
        mark = ('light red', 'default'),

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

        option_selected = ('g85', 'g45'),
        option_selected_key = ('light cyan', 'g50'),
        option_active_selected = ('light red', 'g50'),
    )


class LowLight(Palette):

    """
        Low-color light background
    """
    low = dict(
        background = ('black', 'white'),
        title = ('dark magenta', 'default'),

        # Status bar & heading
        heading = ('white', 'black'),
        heading_key = ('dark blue', 'black'),
        heading_inactive = ('black', 'light gray'),

        # Help
        key = ('dark blue', 'default'),
        head = ('black', 'default'),
        text = ('dark gray', 'default'),

        # Options
        option_selected = ('black', 'light gray'),
        option_selected_key = ('dark blue', 'light gray'),
        option_active = ('light red', 'default'),
        option_active_selected = ('light red', 'light gray'),

        # List and Connections
        method = ('dark cyan', 'default'),
        focus = ('black', 'default'),

        code_200 = ('dark green', 'default'),
        code_300 = ('light blue', 'default'),
        code_400 = ('dark red', 'default'),
        code_500 = ('dark red', 'default'),
        code_other = ('light red', 'default'),

        error = ('light red', 'default'),
        warn = ('brown', 'default'),

        header = ('dark blue', 'default'),
        highlight = ('black,bold', 'default'),
        intercept = ('brown', 'default'),
        replay = ('dark green', 'default'),
        mark = ('dark red', 'default'),

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
        background = ('black', 'g100'),
        heading = ('g99', '#08f'),
        heading_key = ('#0ff,bold', '#08f'),
        heading_inactive = ('g35', 'g85'),
        replay = ('#0a0,bold', 'default'),

        option_selected = ('black', 'g85'),
        option_selected_key = ('dark blue', 'g85'),
        option_active_selected = ('light red', 'g85'),
    )


# Solarized palette in Urwid-style terminal high-colour offsets
# See: http://ethanschoonover.com/solarized
sol_base03 = "h234"
sol_base02 = "h235"
sol_base01 = "h240"
sol_base00 = "h241"
sol_base0 = "h244"
sol_base1 = "h245"
sol_base2 = "h254"
sol_base3 = "h230"
sol_yellow = "h136"
sol_orange = "h166"
sol_red = "h160"
sol_magenta = "h125"
sol_violet = "h61"
sol_blue = "h33"
sol_cyan = "h37"
sol_green = "h64"


class SolarizedLight(LowLight):
    high = dict(
        background = (sol_base00, sol_base3),
        title = (sol_cyan, 'default'),
        text = (sol_base00, 'default'),

        # Status bar & heading
        heading = (sol_base2, sol_base02),
        heading_key = (sol_blue, sol_base03),
        heading_inactive = (sol_base03, sol_base1),

        # Help
        key = (sol_blue, 'default',),
        head = (sol_base00, 'default'),

        # Options
        option_selected = (sol_base03, sol_base2),
        option_selected_key = (sol_blue, sol_base2),
        option_active = (sol_orange, 'default'),
        option_active_selected = (sol_orange, sol_base2),

        # List and Connections
        method = (sol_cyan, 'default'),
        focus = (sol_base01, 'default'),

        code_200 = (sol_green, 'default'),
        code_300 = (sol_blue, 'default'),
        code_400 = (sol_orange, 'default',),
        code_500 = (sol_red, 'default'),
        code_other = (sol_magenta, 'default'),

        error = (sol_red, 'default'),
        warn = (sol_orange, 'default'),

        header = (sol_blue, 'default'),
        highlight = (sol_base01, 'default'),
        intercept = (sol_red, 'default',),
        replay = (sol_green, 'default',),

        # Hex view
        offset = (sol_cyan, 'default'),

        # Grid Editor
        focusfield = (sol_base00, sol_base2),
        focusfield_error = (sol_red, sol_base2),
        field_error = (sol_red, 'default'),
        editfield = (sol_base01, 'default'),
    )


class SolarizedDark(LowDark):
    high = dict(
        background = (sol_base2, sol_base03),
        title = (sol_blue, 'default'),
        text = (sol_base1, 'default'),

        # Status bar & heading
        heading = (sol_base2, sol_base01),
        heading_key = (sol_blue + ",bold", sol_base01),
        heading_inactive = (sol_base1, sol_base02),

        # Help
        key = (sol_blue, 'default',),
        head = (sol_base2, 'default'),

        # Options
        option_selected = (sol_base03, sol_base00),
        option_selected_key = (sol_blue, sol_base00),
        option_active = (sol_orange, 'default'),
        option_active_selected = (sol_orange, sol_base00),

        # List and Connections
        method = (sol_cyan, 'default'),
        focus = (sol_base1, 'default'),

        code_200 = (sol_green, 'default'),
        code_300 = (sol_blue, 'default'),
        code_400 = (sol_orange, 'default',),
        code_500 = (sol_red, 'default'),
        code_other = (sol_magenta, 'default'),

        error = (sol_red, 'default'),
        warn = (sol_orange, 'default'),

        header = (sol_blue, 'default'),
        highlight = (sol_base01, 'default'),
        intercept = (sol_red, 'default',),
        replay = (sol_green, 'default',),

        # Hex view
        offset = (sol_cyan, 'default'),

        # Grid Editor
        focusfield = (sol_base0, sol_base02),
        focusfield_error = (sol_red, sol_base02),
        field_error = (sol_red, 'default'),
        editfield = (sol_base1, 'default'),
    )


DEFAULT = "dark"
palettes = {
    "lowlight": LowLight(),
    "lowdark": LowDark(),
    "light": Light(),
    "dark": Dark(),
    "solarized_light": SolarizedLight(),
    "solarized_dark": SolarizedDark(),
}
