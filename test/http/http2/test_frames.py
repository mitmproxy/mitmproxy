from io import BytesIO

from netlib import tcp, tutils
from netlib.http.http2.frame import *


def hex_to_file(data):
    data = data.decode('hex')
    return tcp.Reader(BytesIO(data))


def test_invalid_flags():
    tutils.raises(
        ValueError,
        DataFrame,
        flags=ContinuationFrame.FLAG_END_HEADERS,
        stream_id=0x1234567,
        payload='foobar')


def test_frame_equality():
    a = DataFrame(
        length=6,
        flags=Frame.FLAG_END_STREAM,
        stream_id=0x1234567,
        payload='foobar')
    b = DataFrame(
        length=6,
        flags=Frame.FLAG_END_STREAM,
        stream_id=0x1234567,
        payload='foobar')
    assert a == b


def test_too_large_frames():
    f = DataFrame(
        length=9000,
        flags=Frame.FLAG_END_STREAM,
        stream_id=0x1234567,
        payload='foobar' * 3000)
    tutils.raises(HttpSyntaxException, f.to_bytes)


def test_data_frame_to_bytes():
    f = DataFrame(
        length=6,
        flags=Frame.FLAG_END_STREAM,
        stream_id=0x1234567,
        payload='foobar')
    assert f.to_bytes().encode('hex') == '000006000101234567666f6f626172'

    f = DataFrame(
        length=11,
        flags=(Frame.FLAG_END_STREAM | Frame.FLAG_PADDED),
        stream_id=0x1234567,
        payload='foobar',
        pad_length=3)
    assert f.to_bytes().encode('hex') == '00000a00090123456703666f6f626172000000'

    f = DataFrame(
        length=6,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        payload='foobar')
    tutils.raises(ValueError, f.to_bytes)


def test_data_frame_from_bytes():
    f = Frame.from_file(hex_to_file('000006000101234567666f6f626172'))
    assert isinstance(f, DataFrame)
    assert f.length == 6
    assert f.TYPE == DataFrame.TYPE
    assert f.flags == Frame.FLAG_END_STREAM
    assert f.stream_id == 0x1234567
    assert f.payload == 'foobar'

    f = Frame.from_file(hex_to_file('00000a00090123456703666f6f626172000000'))
    assert isinstance(f, DataFrame)
    assert f.length == 10
    assert f.TYPE == DataFrame.TYPE
    assert f.flags == Frame.FLAG_END_STREAM | Frame.FLAG_PADDED
    assert f.stream_id == 0x1234567
    assert f.payload == 'foobar'


def test_data_frame_human_readable():
    f = DataFrame(
        length=11,
        flags=(Frame.FLAG_END_STREAM | Frame.FLAG_PADDED),
        stream_id=0x1234567,
        payload='foobar',
        pad_length=3)
    assert f.human_readable()


def test_headers_frame_to_bytes():
    f = HeadersFrame(
        length=6,
        flags=(Frame.FLAG_NO_FLAGS),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'))
    assert f.to_bytes().encode('hex') == '000007010001234567668594e75e31d9'

    f = HeadersFrame(
        length=10,
        flags=(HeadersFrame.FLAG_PADDED),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'),
        pad_length=3)
    assert f.to_bytes().encode('hex') == '00000b01080123456703668594e75e31d9000000'

    f = HeadersFrame(
        length=10,
        flags=(HeadersFrame.FLAG_PRIORITY),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'),
        exclusive=True,
        stream_dependency=0x7654321,
        weight=42)
    assert f.to_bytes().encode('hex') == '00000c012001234567876543212a668594e75e31d9'

    f = HeadersFrame(
        length=14,
        flags=(HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'),
        pad_length=3,
        exclusive=True,
        stream_dependency=0x7654321,
        weight=42)
    assert f.to_bytes().encode('hex') == '00001001280123456703876543212a668594e75e31d9000000'

    f = HeadersFrame(
        length=14,
        flags=(HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'),
        pad_length=3,
        exclusive=False,
        stream_dependency=0x7654321,
        weight=42)
    assert f.to_bytes().encode('hex') == '00001001280123456703076543212a668594e75e31d9000000'

    f = HeadersFrame(
        length=6,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        header_block_fragment='668594e75e31d9'.decode('hex'))
    tutils.raises(ValueError, f.to_bytes)


def test_headers_frame_from_bytes():
    f = Frame.from_file(hex_to_file(
        '000007010001234567668594e75e31d9'))
    assert isinstance(f, HeadersFrame)
    assert f.length == 7
    assert f.TYPE == HeadersFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == '668594e75e31d9'.decode('hex')

    f = Frame.from_file(hex_to_file(
        '00000b01080123456703668594e75e31d9000000'))
    assert isinstance(f, HeadersFrame)
    assert f.length == 11
    assert f.TYPE == HeadersFrame.TYPE
    assert f.flags == HeadersFrame.FLAG_PADDED
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == '668594e75e31d9'.decode('hex')

    f = Frame.from_file(hex_to_file(
        '00000c012001234567876543212a668594e75e31d9'))
    assert isinstance(f, HeadersFrame)
    assert f.length == 12
    assert f.TYPE == HeadersFrame.TYPE
    assert f.flags == HeadersFrame.FLAG_PRIORITY
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == '668594e75e31d9'.decode('hex')
    assert f.exclusive == True
    assert f.stream_dependency == 0x7654321
    assert f.weight == 42

    f = Frame.from_file(hex_to_file(
        '00001001280123456703876543212a668594e75e31d9000000'))
    assert isinstance(f, HeadersFrame)
    assert f.length == 16
    assert f.TYPE == HeadersFrame.TYPE
    assert f.flags == HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == '668594e75e31d9'.decode('hex')
    assert f.exclusive == True
    assert f.stream_dependency == 0x7654321
    assert f.weight == 42

    f = Frame.from_file(hex_to_file(
        '00001001280123456703076543212a668594e75e31d9000000'))
    assert isinstance(f, HeadersFrame)
    assert f.length == 16
    assert f.TYPE == HeadersFrame.TYPE
    assert f.flags == HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == '668594e75e31d9'.decode('hex')
    assert f.exclusive == False
    assert f.stream_dependency == 0x7654321
    assert f.weight == 42


def test_headers_frame_human_readable():
    f = HeadersFrame(
        length=7,
        flags=(HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY),
        stream_id=0x1234567,
        header_block_fragment=b'',
        pad_length=3,
        exclusive=False,
        stream_dependency=0x7654321,
        weight=42)
    assert f.human_readable()

    f = HeadersFrame(
        length=14,
        flags=(HeadersFrame.FLAG_PADDED | HeadersFrame.FLAG_PRIORITY),
        stream_id=0x1234567,
        header_block_fragment='668594e75e31d9'.decode('hex'),
        pad_length=3,
        exclusive=False,
        stream_dependency=0x7654321,
        weight=42)
    assert f.human_readable()


def test_priority_frame_to_bytes():
    f = PriorityFrame(
        length=5,
        flags=(Frame.FLAG_NO_FLAGS),
        stream_id=0x1234567,
        exclusive=True,
        stream_dependency=0x0,
        weight=42)
    assert f.to_bytes().encode('hex') == '000005020001234567800000002a'

    f = PriorityFrame(
        length=5,
        flags=(Frame.FLAG_NO_FLAGS),
        stream_id=0x1234567,
        exclusive=False,
        stream_dependency=0x7654321,
        weight=21)
    assert f.to_bytes().encode('hex') == '0000050200012345670765432115'

    f = PriorityFrame(
        length=5,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        stream_dependency=0x1234567)
    tutils.raises(ValueError, f.to_bytes)


def test_priority_frame_from_bytes():
    f = Frame.from_file(hex_to_file('000005020001234567876543212a'))
    assert isinstance(f, PriorityFrame)
    assert f.length == 5
    assert f.TYPE == PriorityFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x1234567
    assert f.exclusive == True
    assert f.stream_dependency == 0x7654321
    assert f.weight == 42

    f = Frame.from_file(hex_to_file('0000050200012345670765432115'))
    assert isinstance(f, PriorityFrame)
    assert f.length == 5
    assert f.TYPE == PriorityFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x1234567
    assert f.exclusive == False
    assert f.stream_dependency == 0x7654321
    assert f.weight == 21


def test_priority_frame_human_readable():
    f = PriorityFrame(
        length=5,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        exclusive=False,
        stream_dependency=0x7654321,
        weight=21)
    assert f.human_readable()


def test_rst_stream_frame_to_bytes():
    f = RstStreamFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        error_code=0x7654321)
    assert f.to_bytes().encode('hex') == '00000403000123456707654321'

    f = RstStreamFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0)
    tutils.raises(ValueError, f.to_bytes)


def test_rst_stream_frame_from_bytes():
    f = Frame.from_file(hex_to_file('00000403000123456707654321'))
    assert isinstance(f, RstStreamFrame)
    assert f.length == 4
    assert f.TYPE == RstStreamFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x1234567
    assert f.error_code == 0x07654321


def test_rst_stream_frame_human_readable():
    f = RstStreamFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        error_code=0x7654321)
    assert f.human_readable()


def test_settings_frame_to_bytes():
    f = SettingsFrame(
        length=0,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0)
    assert f.to_bytes().encode('hex') == '000000040000000000'

    f = SettingsFrame(
        length=0,
        flags=SettingsFrame.FLAG_ACK,
        stream_id=0x0)
    assert f.to_bytes().encode('hex') == '000000040100000000'

    f = SettingsFrame(
        length=6,
        flags=SettingsFrame.FLAG_ACK,
        stream_id=0x0,
        settings={
            SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 1})
    assert f.to_bytes().encode('hex') == '000006040100000000000200000001'

    f = SettingsFrame(
        length=12,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        settings={
            SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 1,
            SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS: 0x12345678})
    assert f.to_bytes().encode('hex') == '00000c040000000000000200000001000312345678'

    f = SettingsFrame(
        length=0,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567)
    tutils.raises(ValueError, f.to_bytes)


def test_settings_frame_from_bytes():
    f = Frame.from_file(hex_to_file('000000040000000000'))
    assert isinstance(f, SettingsFrame)
    assert f.length == 0
    assert f.TYPE == SettingsFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0

    f = Frame.from_file(hex_to_file('000000040100000000'))
    assert isinstance(f, SettingsFrame)
    assert f.length == 0
    assert f.TYPE == SettingsFrame.TYPE
    assert f.flags == SettingsFrame.FLAG_ACK
    assert f.stream_id == 0x0

    f = Frame.from_file(hex_to_file('000006040100000000000200000001'))
    assert isinstance(f, SettingsFrame)
    assert f.length == 6
    assert f.TYPE == SettingsFrame.TYPE
    assert f.flags == SettingsFrame.FLAG_ACK, 0x0
    assert f.stream_id == 0x0
    assert len(f.settings) == 1
    assert f.settings[SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH] == 1

    f = Frame.from_file(hex_to_file(
        '00000c040000000000000200000001000312345678'))
    assert isinstance(f, SettingsFrame)
    assert f.length == 12
    assert f.TYPE == SettingsFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0
    assert len(f.settings) == 2
    assert f.settings[SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH] == 1
    assert f.settings[SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS] == 0x12345678


def test_settings_frame_human_readable():
    f = SettingsFrame(
        length=12,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        settings={})
    assert f.human_readable()

    f = SettingsFrame(
        length=12,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        settings={
            SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 1,
            SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS: 0x12345678})
    assert f.human_readable()


def test_push_promise_frame_to_bytes():
    f = PushPromiseFrame(
        length=10,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        promised_stream=0x7654321,
        header_block_fragment='foobar')
    assert f.to_bytes().encode('hex') == '00000a05000123456707654321666f6f626172'

    f = PushPromiseFrame(
        length=14,
        flags=HeadersFrame.FLAG_PADDED,
        stream_id=0x1234567,
        promised_stream=0x7654321,
        header_block_fragment='foobar',
        pad_length=3)
    assert f.to_bytes().encode('hex') == '00000e0508012345670307654321666f6f626172000000'

    f = PushPromiseFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        promised_stream=0x1234567)
    tutils.raises(ValueError, f.to_bytes)

    f = PushPromiseFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        promised_stream=0x0)
    tutils.raises(ValueError, f.to_bytes)


def test_push_promise_frame_from_bytes():
    f = Frame.from_file(hex_to_file('00000a05000123456707654321666f6f626172'))
    assert isinstance(f, PushPromiseFrame)
    assert f.length == 10
    assert f.TYPE == PushPromiseFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == 'foobar'

    f = Frame.from_file(hex_to_file(
        '00000e0508012345670307654321666f6f626172000000'))
    assert isinstance(f, PushPromiseFrame)
    assert f.length == 14
    assert f.TYPE == PushPromiseFrame.TYPE
    assert f.flags == PushPromiseFrame.FLAG_PADDED
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == 'foobar'


def test_push_promise_frame_human_readable():
    f = PushPromiseFrame(
        length=14,
        flags=HeadersFrame.FLAG_PADDED,
        stream_id=0x1234567,
        promised_stream=0x7654321,
        header_block_fragment='foobar',
        pad_length=3)
    assert f.human_readable()


def test_ping_frame_to_bytes():
    f = PingFrame(
        length=8,
        flags=PingFrame.FLAG_ACK,
        stream_id=0x0,
        payload=b'foobar')
    assert f.to_bytes().encode('hex') == '000008060100000000666f6f6261720000'

    f = PingFrame(
        length=8,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        payload=b'foobardeadbeef')
    assert f.to_bytes().encode('hex') == '000008060000000000666f6f6261726465'

    f = PingFrame(
        length=8,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567)
    tutils.raises(ValueError, f.to_bytes)


def test_ping_frame_from_bytes():
    f = Frame.from_file(hex_to_file('000008060100000000666f6f6261720000'))
    assert isinstance(f, PingFrame)
    assert f.length == 8
    assert f.TYPE == PingFrame.TYPE
    assert f.flags == PingFrame.FLAG_ACK
    assert f.stream_id == 0x0
    assert f.payload == b'foobar\0\0'

    f = Frame.from_file(hex_to_file('000008060000000000666f6f6261726465'))
    assert isinstance(f, PingFrame)
    assert f.length == 8
    assert f.TYPE == PingFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0
    assert f.payload == b'foobarde'


def test_ping_frame_human_readable():
    f = PingFrame(
        length=8,
        flags=PingFrame.FLAG_ACK,
        stream_id=0x0,
        payload=b'foobar')
    assert f.human_readable()


def test_goaway_frame_to_bytes():
    f = GoAwayFrame(
        length=8,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        last_stream=0x1234567,
        error_code=0x87654321,
        data=b'')
    assert f.to_bytes().encode('hex') == '0000080700000000000123456787654321'

    f = GoAwayFrame(
        length=14,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        last_stream=0x1234567,
        error_code=0x87654321,
        data=b'foobar')
    assert f.to_bytes().encode('hex') == '00000e0700000000000123456787654321666f6f626172'

    f = GoAwayFrame(
        length=8,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        last_stream=0x1234567,
        error_code=0x87654321)
    tutils.raises(ValueError, f.to_bytes)


def test_goaway_frame_from_bytes():
    f = Frame.from_file(hex_to_file(
        '0000080700000000000123456787654321'))
    assert isinstance(f, GoAwayFrame)
    assert f.length == 8
    assert f.TYPE == GoAwayFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0
    assert f.last_stream == 0x1234567
    assert f.error_code == 0x87654321
    assert f.data == b''

    f = Frame.from_file(hex_to_file(
        '00000e0700000000000123456787654321666f6f626172'))
    assert isinstance(f, GoAwayFrame)
    assert f.length == 14
    assert f.TYPE == GoAwayFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0
    assert f.last_stream == 0x1234567
    assert f.error_code == 0x87654321
    assert f.data == b'foobar'


def test_go_away_frame_human_readable():
    f = GoAwayFrame(
        length=14,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        last_stream=0x1234567,
        error_code=0x87654321,
        data=b'foobar')
    assert f.human_readable()


def test_window_update_frame_to_bytes():
    f = WindowUpdateFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        window_size_increment=0x1234567)
    assert f.to_bytes().encode('hex') == '00000408000000000001234567'

    f = WindowUpdateFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        window_size_increment=0x7654321)
    assert f.to_bytes().encode('hex') == '00000408000123456707654321'

    f = WindowUpdateFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x0,
        window_size_increment=0xdeadbeef)
    tutils.raises(ValueError, f.to_bytes)

    f = WindowUpdateFrame(4, Frame.FLAG_NO_FLAGS, 0x0, window_size_increment=0)
    tutils.raises(ValueError, f.to_bytes)


def test_window_update_frame_from_bytes():
    f = Frame.from_file(hex_to_file('00000408000000000001234567'))
    assert isinstance(f, WindowUpdateFrame)
    assert f.length == 4
    assert f.TYPE == WindowUpdateFrame.TYPE
    assert f.flags == Frame.FLAG_NO_FLAGS
    assert f.stream_id == 0x0
    assert f.window_size_increment == 0x1234567


def test_window_update_frame_human_readable():
    f = WindowUpdateFrame(
        length=4,
        flags=Frame.FLAG_NO_FLAGS,
        stream_id=0x1234567,
        window_size_increment=0x7654321)
    assert f.human_readable()


def test_continuation_frame_to_bytes():
    f = ContinuationFrame(
        length=6,
        flags=ContinuationFrame.FLAG_END_HEADERS,
        stream_id=0x1234567,
        header_block_fragment='foobar')
    assert f.to_bytes().encode('hex') == '000006090401234567666f6f626172'

    f = ContinuationFrame(
        length=6,
        flags=ContinuationFrame.FLAG_END_HEADERS,
        stream_id=0x0,
        header_block_fragment='foobar')
    tutils.raises(ValueError, f.to_bytes)


def test_continuation_frame_from_bytes():
    f = Frame.from_file(hex_to_file('000006090401234567666f6f626172'))
    assert isinstance(f, ContinuationFrame)
    assert f.length == 6
    assert f.TYPE == ContinuationFrame.TYPE
    assert f.flags == ContinuationFrame.FLAG_END_HEADERS
    assert f.stream_id == 0x1234567
    assert f.header_block_fragment == 'foobar'


def test_continuation_frame_human_readable():
    f = ContinuationFrame(
        length=6,
        flags=ContinuationFrame.FLAG_END_HEADERS,
        stream_id=0x1234567,
        header_block_fragment='foobar')
    assert f.human_readable()
