from .. import utils, odict, tcp
from frame import *

# "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
CLIENT_CONNECTION_PREFACE = '505249202a20485454502f322e300d0a0d0a534d0d0a0d0a'

ERROR_CODES = utils.BiDi(
    NO_ERROR=0x0,
    PROTOCOL_ERROR=0x1,
    INTERNAL_ERROR=0x2,
    FLOW_CONTROL_ERROR=0x3,
    SETTINGS_TIMEOUT=0x4,
    STREAM_CLOSED=0x5,
    FRAME_SIZE_ERROR=0x6,
    REFUSED_STREAM=0x7,
    CANCEL=0x8,
    COMPRESSION_ERROR=0x9,
    CONNECT_ERROR=0xa,
    ENHANCE_YOUR_CALM=0xb,
    INADEQUATE_SECURITY=0xc,
    HTTP_1_1_REQUIRED=0xd
)


class H2Client(tcp.TCPClient):
    ALPN_PROTO_H2 = b'h2'

    DEFAULT_SETTINGS = {
        SettingsFrame.SETTINGS.SETTINGS_HEADER_TABLE_SIZE: 4096,
        SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 1,
        SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS: None,
        SettingsFrame.SETTINGS.SETTINGS_INITIAL_WINDOW_SIZE: 2 ** 16 - 1,
        SettingsFrame.SETTINGS.SETTINGS_MAX_FRAME_SIZE: 2 ** 14,
        SettingsFrame.SETTINGS.SETTINGS_MAX_HEADER_LIST_SIZE: None,
    }

    def __init__(self, address, source_address=None):
        super(H2Client, self).__init__(address, source_address)
        self.settings = self.DEFAULT_SETTINGS.copy()

    def connect(self, send_preface=True):
        super(H2Client, self).connect()
        self.convert_to_ssl(alpn_protos=[self.ALPN_PROTO_H2])

        alp = self.get_alpn_proto_negotiated()
        if alp != b'h2':
            raise NotImplementedError(
                "H2Client can not handle unknown protocol: %s" %
                alp)
        print "-> Successfully negotiated 'h2' application layer protocol."

        if send_preface:
            self.wfile.write(bytes(CLIENT_CONNECTION_PREFACE.decode('hex')))
            self.send_frame(SettingsFrame())

            frame = Frame.from_file(self.rfile)
            print frame.human_readable()
            assert isinstance(frame, SettingsFrame)
            self.apply_settings(frame.settings)

            print "-> Connection Preface completed."

        print "-> H2Client is ready..."

    def send_frame(self, frame):
        self.wfile.write(frame.to_bytes())
        self.wfile.flush()

    def read_frame(self):
        frame = Frame.from_file(self.rfile)
        if isinstance(frame, SettingsFrame):
            self.apply_settings(frame.settings)

        return frame

    def apply_settings(self, settings):
        for setting, value in settings.items():
            old_value = self.settings[setting]
            if not old_value:
                old_value = '-'

            self.settings[setting] = value
            print "-> Setting changed: %s to %d (was %s)" %
                (SettingsFrame.SETTINGS.get_name(setting),
                 value,
                 str(old_value))

        self.send_frame(SettingsFrame(flags=Frame.FLAG_ACK))
        print "-> New settings acknowledged."
