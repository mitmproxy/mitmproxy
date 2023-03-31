import io

from kaitaistruct import KaitaiStream

from . import base
from mitmproxy.contrib.kaitaistruct import google_protobuf


def write_buf(out, field_tag, body, indent_level):
    if body is not None:
        out.write(
            "{: <{level}}{}: {}\n".format(
                "",
                field_tag,
                body if isinstance(body, int) else str(body, "utf-8"),
                level=indent_level,
            )
        )
    elif field_tag is not None:
        out.write(" " * indent_level + str(field_tag) + " {\n")
    else:
        out.write(" " * indent_level + "}\n")


def _parse_proto(raw: bytes) -> list[google_protobuf.GoogleProtobuf.Pair]:
    """Parse a bytestring into protobuf pairs and make sure that all pairs have a valid wire type."""
    buf = google_protobuf.GoogleProtobuf(KaitaiStream(io.BytesIO(raw)))
    for pair in buf.pairs:
        if not isinstance(
            pair.wire_type, google_protobuf.GoogleProtobuf.Pair.WireTypes
        ):
            raise ValueError("Not a protobuf.")
    return buf.pairs


def format_pbuf(raw):
    out = io.StringIO()
    stack = []

    try:
        pairs = _parse_proto(raw)
    except Exception:
        return False
    stack.extend([(pair, 0) for pair in pairs[::-1]])

    while len(stack):
        pair, indent_level = stack.pop()

        if pair.wire_type == pair.WireTypes.group_start:
            body = None
        elif pair.wire_type == pair.WireTypes.group_end:
            body = None
            pair._m_field_tag = None
        elif pair.wire_type == pair.WireTypes.len_delimited:
            body = pair.value.body
        elif pair.wire_type == pair.WireTypes.varint:
            body = pair.value.value
        else:
            body = pair.value

        try:
            pairs = _parse_proto(body)  # type: ignore
            stack.extend([(pair, indent_level + 2) for pair in pairs[::-1]])
            write_buf(out, pair.field_tag, None, indent_level)
        except Exception:
            write_buf(out, pair.field_tag, body, indent_level)

        if stack:
            prev_level = stack[-1][1]
        else:
            prev_level = 0

        if prev_level < indent_level:
            levels = int((indent_level - prev_level) / 2)
            for i in range(1, levels + 1):
                write_buf(out, None, None, indent_level - i * 2)

    return out.getvalue()


class ViewProtobuf(base.View):
    """Human friendly view of protocol buffers
    The view uses the protoc compiler to decode the binary
    """

    name = "Protocol Buffer"
    __content_types = [
        "application/x-protobuf",
        "application/x-protobuffer",
    ]

    def __call__(self, data, **metadata):
        decoded = format_pbuf(data)
        if not decoded:
            raise ValueError("Failed to parse input.")

        return "Protobuf", base.format_text(decoded)

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(bool(data) and content_type in self.__content_types)
