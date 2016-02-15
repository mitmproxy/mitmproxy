import time

from netlib import websockets
from .. import language
from netlib.exceptions import NetlibException


class WebsocketsProtocol:

    def __init__(self, pathod_handler):
        self.pathod_handler = pathod_handler

    def handle_websocket(self, logger):
        while True:
            with logger.ctx() as lg:
                started = time.time()
                try:
                    frm = websockets.Frame.from_file(self.pathod_handler.rfile)
                except NetlibException as e:
                    lg("Error reading websocket frame: %s" % e)
                    break
                ended = time.time()
                lg(frm.human_readable())
            retlog = dict(
                type="inbound",
                protocol="websockets",
                started=started,
                duration=ended - started,
                frame=dict(
                ),
                cipher=None,
            )
            if self.pathod_handler.ssl_established:
                retlog["cipher"] = self.pathod_handler.get_current_cipher()
            self.pathod_handler.addlog(retlog)
            ld = language.websockets.NESTED_LEADER
            if frm.payload.startswith(ld):
                nest = frm.payload[len(ld):]
                try:
                    wf_gen = language.parse_websocket_frame(nest)
                except language.exceptions.ParseException as v:
                    logger.write(
                        "Parse error in reflected frame specifcation:"
                        " %s" % v.msg
                    )
                    return None, None
                for frm in wf_gen:
                    with logger.ctx() as lg:
                        frame_log = language.serve(
                            frm,
                            self.pathod_handler.wfile,
                            self.pathod_handler.settings
                        )
                        lg("crafting websocket spec: %s" % frame_log["spec"])
                        self.pathod_handler.addlog(frame_log)
        return self.handle_websocket, None
