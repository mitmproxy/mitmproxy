import time

from mitmproxy.utils import strutils
from mitmproxy.utils import human


def write_raw(fp, lines, timestamp=True):
    if fp:
        if timestamp:
            fp.write(human.format_timestamp(time.time()))
        for i in lines:
            fp.write(i)
        fp.write("\n")
        fp.flush()


class LogCtx:

    def __init__(self, fp, hex, timestamp, rfile, wfile):
        self.lines = []
        self.fp = fp
        self.suppressed = False
        self.hex = hex
        self.timestamp = timestamp
        self.rfile, self.wfile = rfile, wfile

    def __enter__(self):
        if self.wfile:
            self.wfile.start_log()
        if self.rfile:
            self.rfile.start_log()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        wlog = self.wfile.get_log() if self.wfile else None
        rlog = self.rfile.get_log() if self.rfile else None
        if self.suppressed or not self.fp:
            return
        if wlog:
            self("Bytes written:")
            self.dump(wlog, self.hex)
        if rlog:
            self("Bytes read:")
            self.dump(rlog, self.hex)
        if self.lines:
            write_raw(
                self.fp,
                [
                    "\n".join(self.lines),
                ],
                timestamp = self.timestamp
            )
        if exc_value:
            raise exc_value

    def suppress(self):
        self.suppressed = True

    def dump(self, data, hexdump):
        if hexdump:
            for line in strutils.hexdump(data):
                self("\t%s %s %s" % line)
        else:
            data = strutils.always_str(
                strutils.escape_control_characters(
                    data
                        .decode("ascii", "replace")
                        .replace(u"\ufffd", u".")
                )
            )
            for i in data.split("\n"):
                self("\t%s" % i)

    def __call__(self, line):
        self.lines.append(line)


class ConnectionLogger:
    def __init__(self, fp, hex, timestamp, rfile, wfile):
        self.fp = fp
        self.hex = hex
        self.rfile, self.wfile = rfile, wfile
        self.timestamp = timestamp

    def ctx(self):
        return LogCtx(self.fp, self.hex, self.timestamp, self.rfile, self.wfile)

    def write(self, lines):
        write_raw(self.fp, lines, timestamp=self.timestamp)
