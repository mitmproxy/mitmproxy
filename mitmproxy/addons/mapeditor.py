import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


def parse_mapeditor(mexpr):
    """
        Returns a (pattern, path_to_file) tuple

        example:
            ~u .*://example.com/script.js:MAP_TO:/etc/hostname
            ^                            ^      ^            ^
            |------filter_expression-----|--sep-|path_to_file|
    """
    parts = mexpr.split(":MAP_TO:")
    if len(parts) != 2:
        raise exceptions.OptionsError(
            "Invalid map editor specifier: %s" % mexpr
        )
    return parts[0], parts[1]


# performance optimize
# 0b01 for request
# 0b10 for response
mapchoice_option_mapper = {
    "request": 0b01,
    "response": 0b10,
}


class MapEditor:
    def __init__(self):
        self.map_list = []
        self.map_choice = 0b10

    def load(self, loader):
        loader.add_option(
            "mapeditor", typing.Sequence[str], [],
            """
            map files like "pattern:MAP_TO:/path/to/local/file"
            all response body matched by 'pattern' will be replaced to the content of file
            """
        )
        loader.add_option(
            "mapeditor_choice", str, "response",
            """
            select whether request or response or both to replace.
            by default, mapeditor only replace response content
            """,
            choices=sorted([
                "response",
                "request",
                "response + request",
            ])
        )

    def configure(self, updated):
        self.map_list = []
        for mpatt in ctx.options.mapeditor:
            fpatt, path_to_file = parse_mapeditor(mpatt)

            flt = flowfilter.parse(fpatt)
            if not flt:
                raise exceptions.OptionsError(
                    "Invalid map editor filter pattern: %s" % fpatt
                )
            self.map_list.append((fpatt, path_to_file, flt))
        self.map_choice = mapchoice_option_mapper[ctx.options.mapeditor_choice] | mapchoice_option_mapper[ctx.options.mapeditor_choice]

    def run(self, f, flow):
        for _, path_to_file, flt in self.map_list:
            if flt(f):
                try:
                    with open(path_to_file, "rb") as tmp_f:
                        flow.content = tmp_f.read()
                except Exception:
                    # TODO: add an IO exception
                    raise exceptions.MitmproxyException(
                        "Failed to open file: %s" % path_to_file
                    )

    def request(self, flow):
        if not flow.reply.has_message and self.map_choice & 0b01:
            self.run(flow, flow.request)

    def response(self, flow):
        if not flow.reply.has_message and self.map_choice & 0b10:
            self.run(flow, flow.response)