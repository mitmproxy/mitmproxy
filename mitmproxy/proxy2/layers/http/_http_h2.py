import collections

import h2.config
import h2.connection
import h2.events
import h2.settings
from typing import DefaultDict, Deque, NamedTuple, Optional


class H2ConnectionLogger(h2.config.DummyLogger):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def debug(self, fmtstr, *args):
        """
        No-op logging. Only level needed for now.
        """
        print(f"(debug) h2 {self.name}: {fmtstr % args}")

    def trace(self, fmtstr, *args):
        """
        No-op logging. Only level needed for now.
        """
        print(f"(trace) h2 {self.name}: {fmtstr % args}")


class SendH2Data(NamedTuple):
    data: bytes
    end_stream: bool
    pad_length: Optional[int]


class BufferedH2Connection(h2.connection.H2Connection):
    """
    This class wrap's hyper-h2's H2Connection and adds internal send buffers.
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
            pad_length: Optional[int] = None
    ) -> None:
        """
        Send data on a given stream.

        In contrast to plain h2, this method will not emit
        either FlowControlError or FrameTooLargeError.
        Instead, data is buffered and split up.
        """
        frame_size = len(data)
        if pad_length is not None:
            frame_size += pad_length + 1

        while frame_size > self.max_outbound_frame_size:
            chunk_1 = data[:self.max_outbound_frame_size]
            pad_1 = max(0, self.max_outbound_frame_size - len(data))
            self.send_data(stream_id, chunk_1, end_stream=False, pad_length=pad_1 or None)

            data = data[self.max_outbound_frame_size:]
            if pad_length:
                pad_length -= pad_1
            frame_size -= len(chunk_1) + pad_1

        available_window = self.local_flow_control_window(stream_id)
        if frame_size > available_window:
            self.stream_buffers[stream_id].append(
                SendH2Data(data, end_stream, pad_length)
            )
        else:
            # We can't send right now, so we buffer.
            super().send_data(stream_id, data, end_stream, pad_length)

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
                        pad_length=chunk.pad_length,
                    )
                )
                chunk = SendH2Data(
                    data=chunk.data[:available_window],
                    end_stream=False,
                    pad_length=None,
                )

            super().send_data(stream_id, data=chunk.data, end_stream=chunk.end_stream, pad_length=chunk.pad_length)

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
