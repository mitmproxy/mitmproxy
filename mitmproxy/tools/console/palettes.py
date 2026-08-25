# Low-color themes should ONLY use the standard foreground and background
# colours listed here:
#
# http://urwid.org/manual/displayattributes.html
#
from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence


class Palette:
    _fields = [
        "background",
        "title",
        # Status bar & heading
        "heading",
        "heading_key",
        "heading_inactive",
        # Help
        "key",
        "head",
        "text",
        # Options
        "option_selected",
        "option_active",
        "option_active_selected",
        "option_selected_key",
        # List and Connections
        "method_get",
        "method_post",
        "method_delete",
        "method_other",
        "method_head",
        "method_put",
        "method_http2_push",
        "scheme_http",
        "scheme_https",
        "scheme_ws",
        "scheme_wss",
        "scheme_tcp",
        "scheme_udp",
        "scheme_dns",
        "scheme_quic",
        "scheme_other",
        "url_punctuation",
        "url_domain",
        "url_filename",
        "url_extension",
        "url_query_key",
        "url_query_value",
        "content_none",
        "content_text",
        "content_script",
        "content_media",
        "content_data",
        "content_raw",
        "content_other",
        "focus",
        "code_200",
        "code_300",
        "code_400",
        "code_500",
        "code_other",
        "error",
        "warn",
        "alert",
        "header",
        "highlight",
        "intercept",
        "replay",
        "mark",
        # Contentview Syntax Highlighting
        "name",
        "string",
        "number",
        "boolean",
        "comment",
        "error",
        # TCP flow details
        "from_client",
        "to_client",
        # Grid Editor
        "focusfield",
        "focusfield_error",
        "field_error",
        "editfield",
        # Commander
        "commander_command",
        "commander_invalid",
        "commander_hint",
    ]
    _fields.extend(["gradient_%02d" % i for i in range(100)])
    high: Mapping[str, Sequence[str]] | None = None
    low: Mapping[str, Sequence[str]]

    def palette(self, transparent: bool):
        lst: list[Sequence[str | None]] = []
        highback, lowback = None, None
        if not transparent:
            if self.high and self.high.get("background"):
                highback = self.high["background"][1]
            lowback = self.low["background"][1]

        for i in self._fields:
            if transparent and i == "background":
                lst.append(["background", "default", "default"])
            else:
                v: list[str | None] = [i]
                low = list(self.low[i])
                if lowback and low[1] == "default":
                    low[1] = lowback
                v.extend(low)
                if self.high and i in self.high:
                    v.append(None)
                    high: list[str | None] = list(self.high[i])
                    if highback and high[1] == "default":
                        high[1] = highback
                    v.extend(high)
                elif highback and self.low[i][1] == "default":
                    high = [None, low[0], highback]
                    v.extend(high)
                lst.append(tuple(v))
        return lst


def gen_gradient(palette, cols):
    for i in range(100):
        palette["gradient_%02d" % i] = (cols[i * len(cols) // 100], "default")


def gen_rgb_gradient(palette, cols):
    parts = len(cols) - 1
    for i in range(100):
        p = i / 100
        idx = int(p * parts)
        t0 = cols[idx]
        t1 = cols[idx + 1]
        pp = p * parts % 1
        t = (
            round(t0[0] + (t1[0] - t0[0]) * pp),
            round(t0[1] + (t1[1] - t0[1]) * pp),
            round(t0[2] + (t1[2] - t0[2]) * pp),
        )
        palette["gradient_%02d" % i] = ("#%x%x%x" % t, "default")


class LowDark(Palette):
    """
    Low-color dark background
    """

    low = dict(
        background=("white", "black"),
        title=("white,bold", "default"),
        # Status bar & heading
        heading=("white", "dark blue"),
        heading_key=("light cyan", "dark blue"),
        heading_inactive=("dark gray", "light gray"),
        # Help
        key=("light cyan", "default"),
        head=("white,bold", "default"),
        text=("light gray", "default"),
        # Options
        option_selected=("black", "light gray"),
        option_selected_key=("light cyan", "light gray"),
        option_active=("light red", "default"),
        option_active_selected=("light red", "light gray"),
        # List and Connections
        method_get=("light green", "default"),
        method_post=("brown", "default"),
        method_delete=("light red", "default"),
        method_head=("dark cyan", "default"),
        method_put=("dark red", "default"),
        method_other=("dark magenta", "default"),
        method_http2_push=("dark gray", "default"),
        scheme_http=("dark cyan", "default"),
        scheme_https=("dark green", "default"),
        scheme_ws=("brown", "default"),
        scheme_wss=("dark magenta", "default"),
        scheme_tcp=("dark magenta", "default"),
        scheme_udp=("dark magenta", "default"),
        scheme_dns=("dark blue", "default"),
        scheme_quic=("brown", "default"),
        scheme_other=("dark magenta", "default"),
        url_punctuation=("light gray", "default"),
        url_domain=("white", "default"),
        url_filename=("dark cyan", "default"),
        url_extension=("light gray", "default"),
        url_query_key=("white", "default"),
        url_query_value=("light gray", "default"),
        content_none=("dark gray", "default"),
        content_text=("light gray", "default"),
        content_script=("dark green", "default"),
        content_media=("light blue", "default"),
        content_data=("brown", "default"),
        content_raw=("dark red", "default"),
        content_other=("dark magenta", "default"),
        focus=("yellow", "default"),
        code_200=("dark green", "default"),
        code_300=("light blue", "default"),
        code_400=("light red", "default"),
        code_500=("light red", "default"),
        code_other=("dark red", "default"),
        alert=("light magenta", "default"),
        warn=("brown", "default"),
        error=("light red", "default"),
        header=("dark cyan", "default"),
        highlight=("white,bold", "default"),
        intercept=("brown", "default"),
        replay=("light green", "default"),
        mark=("light red", "default"),
        # Contentview Syntax Highlighting
        name=("dark green", "default"),
        string=("dark blue", "default"),
        number=("light magenta", "default"),
        boolean=("dark magenta", "default"),
        comment=("dark gray", "default"),
        # TCP flow details
        from_client=("light blue", "default"),
        to_client=("light red", "default"),
        # Grid Editor
        focusfield=("black", "light gray"),
        focusfield_error=("dark red", "light gray"),
        field_error=("dark red", "default"),
        editfield=("white", "default"),
        commander_command=("white,bold", "default"),
        commander_invalid=("light red", "default"),
        commander_hint=("dark gray", "default"),
    )
    gen_gradient(
        low,
        ["light red", "yellow", "light green", "dark green", "dark cyan", "dark blue"],
    )


class Dark(LowDark):
    high = dict(
        heading_inactive=("g58", "g11"),
        intercept=("#f60", "default"),
        option_selected=("g85", "g45"),
        option_selected_key=("light cyan", "g50"),
        option_active_selected=("light red", "g50"),
    )


class LowLight(Palette):
    """
    Low-color light background
    """

    low = dict(
        background=("black", "white"),
        title=("dark magenta", "default"),
        # Status bar & heading
        heading=("white", "black"),
        heading_key=("dark blue", "black"),
        heading_inactive=("black", "light gray"),
        # Help
        key=("dark blue", "default"),
        head=("black", "default"),
        text=("dark gray", "default"),
        # Options
        option_selected=("black", "light gray"),
        option_selected_key=("dark blue", "light gray"),
        option_active=("light red", "default"),
        option_active_selected=("light red", "light gray"),
        # List and Connections
        method_get=("dark green", "default"),
        method_post=("brown", "default"),
        method_head=("dark cyan", "default"),
        method_put=("light red", "default"),
        method_delete=("dark red", "default"),
        method_other=("light magenta", "default"),
        method_http2_push=("light gray", "default"),
        scheme_http=("dark cyan", "default"),
        scheme_https=("light green", "default"),
        scheme_ws=("brown", "default"),
        scheme_wss=("light magenta", "default"),
        scheme_tcp=("light magenta", "default"),
        scheme_udp=("light magenta", "default"),
        scheme_dns=("light blue", "default"),
        scheme_quic=("brown", "default"),
        scheme_other=("light magenta", "default"),
        url_punctuation=("dark gray", "default"),
        url_domain=("dark gray", "default"),
        url_filename=("black", "default"),
        url_extension=("dark gray", "default"),
        url_query_key=("light blue", "default"),
        url_query_value=("dark blue", "default"),
        content_none=("black", "default"),
        content_text=("dark gray", "default"),
        content_script=("light green", "default"),
        content_media=("light blue", "default"),
        content_data=("brown", "default"),
        content_raw=("light red", "default"),
        content_other=("light magenta", "default"),
        focus=("black", "default"),
        code_200=("dark green", "default"),
        code_300=("light blue", "default"),
        code_400=("dark red", "default"),
        code_500=("dark red", "default"),
        code_other=("light red", "default"),
        error=("light red", "default"),
        warn=("brown", "default"),
        alert=("light magenta", "default"),
        header=("dark blue", "default"),
        highlight=("black,bold", "default"),
        intercept=("brown", "default"),
        replay=("dark green", "default"),
        mark=("dark red", "default"),
        # Contentview Syntax Highlighting
        name=("dark green", "default"),
        string=("dark blue", "default"),
        number=("light magenta", "default"),
        boolean=("dark magenta", "default"),
        comment=("dark gray", "default"),
        # TCP flow details
        from_client=("dark blue", "default"),
        to_client=("dark red", "default"),
        # Grid Editor
        focusfield=("black", "light gray"),
        focusfield_error=("dark red", "light gray"),
        field_error=("dark red", "black"),
        editfield=("black", "default"),
        commander_command=("dark magenta", "default"),
        commander_invalid=("light red", "default"),
        commander_hint=("light gray", "default"),
    )
    gen_gradient(
        low,
        ["light red", "yellow", "light green", "dark green", "dark cyan", "dark blue"],
    )


class Light(LowLight):
    high = dict(
        background=("black", "g100"),
        heading=("g99", "#08f"),
        heading_key=("#0ff,bold", "#08f"),
        heading_inactive=("g35", "g85"),
        replay=("#0a0,bold", "default"),
        option_selected=("black", "g85"),
        option_selected_key=("dark blue", "g85"),
        option_active_selected=("light red", "g85"),
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
        background=(sol_base00, sol_base3),
        title=(sol_cyan, "default"),
        text=(sol_base00, "default"),
        # Status bar & heading
        heading=(sol_base2, sol_base02),
        heading_key=(sol_blue, sol_base03),
        heading_inactive=(sol_base03, sol_base1),
        # Help
        key=(
            sol_blue,
            "default",
        ),
        head=(sol_base00, "default"),
        # Options
        option_selected=(sol_base03, sol_base2),
        option_selected_key=(sol_blue, sol_base2),
        option_active=(sol_orange, "default"),
        option_active_selected=(sol_orange, sol_base2),
        # List and Connections
        method_get=(sol_green, "default"),
        method_post=(sol_orange, "default"),
        method_head=(sol_cyan, "default"),
        method_put=(sol_red, "default"),
        method_delete=(sol_red, "default"),
        method_other=(sol_magenta, "default"),
        method_http2_push=("light gray", "default"),
        scheme_http=(sol_cyan, "default"),
        scheme_https=("light green", "default"),
        scheme_ws=(sol_orange, "default"),
        scheme_wss=("light magenta", "default"),
        scheme_tcp=("light magenta", "default"),
        scheme_udp=("light magenta", "default"),
        scheme_dns=("light blue", "default"),
        scheme_quic=(sol_orange, "default"),
        scheme_other=("light magenta", "default"),
        url_punctuation=("dark gray", "default"),
        url_domain=("dark gray", "default"),
        url_filename=("black", "default"),
        url_extension=("dark gray", "default"),
        url_query_key=(sol_blue, "default"),
        url_query_value=("dark blue", "default"),
        focus=(sol_base01, "default"),
        code_200=(sol_green, "default"),
        code_300=(sol_blue, "default"),
        code_400=(
            sol_orange,
            "default",
        ),
        code_500=(sol_red, "default"),
        code_other=(sol_magenta, "default"),
        error=(sol_red, "default"),
        warn=(sol_orange, "default"),
        alert=(sol_magenta, "default"),
        header=(sol_blue, "default"),
        highlight=(sol_base01, "default"),
        intercept=(
            sol_red,
            "default",
        ),
        replay=(
            sol_green,
            "default",
        ),
        mark=(sol_base01, "default"),
        # Contentview Syntax Highlighting
        name=(sol_green, "default"),
        string=(sol_cyan, "default"),
        number=(sol_blue, "default"),
        boolean=(sol_magenta, "default"),
        comment=(sol_base1, "default"),
        # TCP flow details
        from_client=(sol_blue, "default"),
        to_client=(sol_red, "default"),
        # Grid Editor
        focusfield=(sol_base00, sol_base2),
        focusfield_error=(sol_red, sol_base2),
        field_error=(sol_red, "default"),
        editfield=(sol_base01, "default"),
        commander_command=(sol_cyan, "default"),
        commander_invalid=(sol_orange, "default"),
        commander_hint=(sol_base1, "default"),
    )


class SolarizedDark(LowDark):
    high = dict(
        background=(sol_base2, sol_base03),
        title=(sol_blue, "default"),
        text=(sol_base1, "default"),
        # Status bar & heading
        heading=(sol_base2, sol_base01),
        heading_key=(sol_blue + ",bold", sol_base01),
        heading_inactive=(sol_base1, sol_base02),
        # Help
        key=(
            sol_blue,
            "default",
        ),
        head=(sol_base2, "default"),
        # Options
        option_selected=(sol_base03, sol_base00),
        option_selected_key=(sol_blue, sol_base00),
        option_active=(sol_orange, "default"),
        option_active_selected=(sol_orange, sol_base00),
        # List and Connections
        focus=(sol_base1, "default"),
        method_get=(sol_green, "default"),
        method_post=(sol_orange, "default"),
        method_delete=(sol_red, "default"),
        method_head=(sol_cyan, "default"),
        method_put=(sol_red, "default"),
        method_other=(sol_magenta, "default"),
        method_http2_push=(sol_base01, "default"),
        url_punctuation=("h242", "default"),
        url_domain=("h252", "default"),
        url_filename=("h132", "default"),
        url_extension=("h96", "default"),
        url_query_key=("h37", "default"),
        url_query_value=("h30", "default"),
        content_none=(sol_base01, "default"),
        content_text=(sol_base1, "default"),
        content_media=(sol_blue, "default"),
        code_200=(sol_green, "default"),
        code_300=(sol_blue, "default"),
        code_400=(
            sol_orange,
            "default",
        ),
        code_500=(sol_red, "default"),
        code_other=(sol_magenta, "default"),
        error=(sol_red, "default"),
        warn=(sol_orange, "default"),
        alert=(sol_magenta, "default"),
        header=(sol_blue, "default"),
        highlight=(sol_base01, "default"),
        intercept=(
            sol_red,
            "default",
        ),
        replay=(
            sol_green,
            "default",
        ),
        mark=(sol_base01, "default"),
        # Contentview Syntax Highlighting
        name=(sol_green, "default"),
        string=(sol_cyan, "default"),
        number=(sol_blue, "default"),
        boolean=(sol_magenta, "default"),
        comment=(sol_base00, "default"),
        # TCP flow details
        from_client=(sol_blue, "default"),
        to_client=(sol_red, "default"),
        # Grid Editor
        focusfield=(sol_base0, sol_base02),
        focusfield_error=(sol_red, sol_base02),
        field_error=(sol_red, "default"),
        editfield=(sol_base1, "default"),
        commander_command=(sol_blue, "default"),
        commander_invalid=(sol_orange, "default"),
        commander_hint=(sol_base00, "default"),
    )
    gen_rgb_gradient(
        high, [(15, 0, 0), (15, 15, 0), (0, 15, 0), (0, 15, 15), (0, 0, 15)]
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
