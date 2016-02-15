import datetime

import netlib.utils
import netlib.tcp
import netlib.http

TIMEFMT = '%d-%m-%y %H:%M:%S'


def write_raw(fp, lines):
    if fp:
        fp.write(
            "%s: " % datetime.datetime.now().strftime(TIMEFMT)
        )
        for i in lines:
            fp.write(i)
        fp.write("\n")
        fp.flush()


class LogCtx(object):

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
        if self.lines:
            write_raw(
                self.fp,
                [
                    "\n".join(self.lines),
                ]
            )
        if exc_value:
            raise exc_type, exc_value, traceback

    def suppress(self):
        self.suppressed = True

    def dump(self, data, hexdump):
        if hexdump:
            for line in netlib.utils.hexdump(data):
                self("\t%s %s %s" % line)
        else:
            for i in netlib.utils.clean_bin(data).split("\n"):
                self("\t%s" % i)

    def __call__(self, line):
        self.lines.append(line)


class ConnectionLogger:
    def __init__(self, fp, hex, rfile, wfile):
        self.fp = fp
        self.hex = hex
        self.rfile, self.wfile = rfile, wfile

    def ctx(self):
        return LogCtx(self.fp, self.hex, self.rfile, self.wfile)

    def write(self, lines):
        write_raw(self.fp, lines)
