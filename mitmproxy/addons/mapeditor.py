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

# TODO: add test for map editor
class MapEditor:
    def __init__(self):
        self.map_list = []

    def load(self, loader):
        loader.add_option(
            "mapeditor", typing.Sequence[str], [],
            """
            map files like "pattern:MAP_TO:/path/to/local/file"
            all response body matched by 'pattern' will be replaced to the content of file
            """
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
    
    def run(self, f, response):
        for _, path_to_file, flt in self.map_list:
            if flt(f):
                try:
                    with open(path_to_file, "rb") as tmp_f:
                        response.content = tmp_f.read()
                except Exception as e:
                    # TODO: add an IO exception
                    raise exceptions.MitmproxyException(
                        "Failed to open file: %s" % path_to_file
                    )
    
    def response(self, flow):
        if not flow.reply.has_message:
            self.run(flow, flow.response)