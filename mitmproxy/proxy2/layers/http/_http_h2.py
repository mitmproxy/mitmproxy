import collections

import h2.config
import h2.connection
import h2.events
import h2.settings
import h2.exceptions
from typing import DefaultDict, Deque, NamedTuple, Optional


class H2ConnectionLogger(h2.config.DummyLogger):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def debug(self, fmtstr, *args):
        print(f"(debug) h2 {self.name}: {fmtstr % args}")

    def trace(self, fmtstr, *args):
        print(f"(trace) h2 {self.name}: {fmtstr % args}")


class SendH2Data(NamedTuple):
    data: bytes
    end_stream: bool


class BufferedH2Connection(h2.connection.H2Connection):
    """
    This class wrap's hyper-h2's H2Connection and adds internal send buffers.

    To simplify implementation, padding is unsupported.
    """
    stream_buffers: DefaultDict[int, Deque[SendH2Data]]

    def __init__(self, config: h2.config.H2Configuration):
        super().__init__(config)
        self.stream_buffers = collections.defaultdict(collections.deque)

    def send_data(
            self,
            stream_id: int,
            data: bytes,
            end_stream: bool = False,
            pad_length: None = None
    ) -> None:
        """
        Send data on a given stream.

        In contrast to plain hyper-h2, this method will not raise if the data cannot be sent immediately.
        Data is split up and buffered internally.
        """
        frame_size = len(data)
        assert pad_length is None

        while frame_size > self.max_outbound_frame_size:
            chunk_data = data[:self.max_outbound_frame_size]
            self.send_data(stream_id, chunk_data, end_stream=False)

            data = data[self.max_outbound_frame_size:]
            frame_size -= len(chunk_data)

        available_window = self.local_flow_control_window(stream_id)
        if frame_size <= available_window:
            super().send_data(stream_id, data, end_stream)
        else:
            # We can't send right now, so we buffer.
            self.stream_buffers[stream_id].append(
                SendH2Data(data, end_stream)
            )

    def receive_data(self, data: bytes):
        events = super().receive_data(data)
        ret = []
        for event in events:
            if isinstance(event, h2.events.WindowUpdated):
                if event.stream_id == 0:
                    self.connection_window_updated()
                else:
                    self.stream_window_updated(event.stream_id)
                continue
            elif isinstance(event, h2.events.RemoteSettingsChanged):
                if h2.settings.SettingCodes.INITIAL_WINDOW_SIZE in event.changed_settings:
                    self.connection_window_updated()
            elif isinstance(event, h2.events.StreamReset):
                self.stream_buffers.pop(event.stream_id, None)
            elif isinstance(event, h2.events.ConnectionTerminated):
                self.stream_buffers.clear()
            ret.append(event)
        return ret

    def stream_window_updated(self, stream_id: int) -> bool:
        """
        The window for a specific stream has updated. Send as much buffered data as possible.
        """
        available_window = self.local_flow_control_window(stream_id)
        sent_any_data = False
        while available_window and stream_id in self.stream_buffers:
            chunk: SendH2Data = self.stream_buffers[stream_id].popleft()
            if len(chunk.data) > available_window:
                # We can't send the entire chunk, so we have to put some bytes back into the buffer.
                self.stream_buffers[stream_id].appendleft(
                    SendH2Data(
                        data=chunk.data[available_window:],
                        end_stream=chunk.end_stream,
                    )
                )
                chunk = SendH2Data(
                    data=chunk.data[:available_window],
                    end_stream=False,
                )

            self.send_data(stream_id, data=chunk.data, end_stream=chunk.end_stream)

            available_window -= len(chunk.data)
            if not self.stream_buffers[stream_id]:
                del self.stream_buffers[stream_id]
            sent_any_data = True

        return sent_any_data

    def connection_window_updated(self):
        """
        The connection window has updated. Send data from buffers in a round-robin fashion.
        """
        sent_any_data = True
        while sent_any_data:
            sent_any_data = False
            for stream_id in list(self.stream_buffers):
                self.stream_buffers[stream_id] = self.stream_buffers.pop(stream_id)  # move to end of dict
                if self.stream_window_updated(stream_id):
                    sent_any_data = True
                    if self.outbound_flow_control_window == 0:
                        return
