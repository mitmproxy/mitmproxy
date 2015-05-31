import datetime

import netlib.utils
import netlib.tcp
import netlib.http

TIMEFMT = '%d-%m-%y %H:%M:%S'


def write(fp, lines):
    if fp:
        fp.write(
            "%s: " % datetime.datetime.now().strftime(TIMEFMT)
        )
        for i in lines:
            fp.write(i)
        fp.flush()


class Log:

    def __init__(self, fp, hex, rfile, wfile):
        self.lines = []
        self.fp = fp
        self.suppressed = False
        self.hex = hex
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
        if exc_type == netlib.tcp.NetLibTimeout:
            self("Timeout")
        elif exc_type in (
            netlib.tcp.NetLibDisconnect,
            netlib.http.HttpErrorConnClosed
        ):
            self("Disconnected")
        elif exc_type == netlib.http.HttpError:
            self("HTTP Error: %s" % exc_value.message)
        write(
            self.fp,
            [
                "\n".join(self.lines),
                "\n"
            ]
        )
        if exc_value:
            raise exc_value

    def suppress(self):
        self.suppressed = True

    def dump(self, data, hexdump):
        if hexdump:
            for line in netlib.utils.hexdump(data):
                self("\t%s %s %s" % line)
        else:
            for i in netlib.utils.cleanBin(data).split("\n"):
                self("\t%s" % i)

    def __call__(self, line):
        self.lines.append(line)
