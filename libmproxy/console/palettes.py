
# Low-color themes should ONLY use the standard foreground and background
# colours listed here:
#
# http://urwid.org/manual/displayattributes.html
#



class Palette:
    _fields = [
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
        'error',
        'header', 'highlight', 'intercept', 'replay',

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
        title = ('white,bold', 'default'),

        # Status bar & heading
        heading = ('light gray', 'dark blue'),
        heading_key = ('light cyan', 'dark blue'),
        heading_inactive = ('white', 'dark gray'),

        # Help
        key = ('light cyan', 'default'),
        head = ('white,bold', 'default'),
        text = ('light gray', 'default'),

        # Options
        option_selected = ('light gray', 'dark blue'),
        option_selected_key = ('light cyan', 'dark blue'),
        option_active = ('light red', 'default'),
        option_active_selected = ('light red', 'dark blue'),

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

        header = ('dark blue', 'default'),
        highlight = ('black,bold', 'default'),
        intercept = ('brown', 'default'),
        replay = ('dark green', 'default'),

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


# Solarized palette in Urwid-style terminal high-colour offsets
# See: http://ethanschoonover.com/solarized
sol_base03 = "h234"
sol_base02 = "h235"
sol_base01 = "h240"
sol_base00 = "h241"
sol_base0  = "h244"
sol_base1  = "h245"
sol_base2  = "h254"
sol_base3  = "h230"
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

        header = (sol_base01, 'default'),
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
        title = (sol_blue, 'default'),
        text = (sol_base1, 'default'),

        # Status bar & heading
        heading = (sol_base2, sol_base01),
        heading_key = (sol_blue+",bold", sol_base01),
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

        header = (sol_base01, 'default'),
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


palettes = {
    "lowlight": LowLight(),
    "lowdark": LowDark(),
    "light": Light(),
    "dark": Dark(),
    "solarized_light": SolarizedLight(),
    "solarized_dark": SolarizedDark(),
}
