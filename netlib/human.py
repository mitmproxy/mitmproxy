import datetime
import time


SIZE_TABLE = [
    ("b", 1024 ** 0),
    ("k", 1024 ** 1),
    ("m", 1024 ** 2),
    ("g", 1024 ** 3),
    ("t", 1024 ** 4),
]

SIZE_UNITS = dict(SIZE_TABLE)


def pretty_size(size):
    for bottom, top in zip(SIZE_TABLE, SIZE_TABLE[1:]):
        if bottom[1] <= size < top[1]:
            suf = bottom[0]
            lim = bottom[1]
            x = round(size / lim, 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf
    return "%s%s" % (size, SIZE_TABLE[0][0])


def parse_size(s):
    try:
        return int(s)
    except ValueError:
        pass
    for i in SIZE_UNITS.keys():
        if s.endswith(i):
            try:
                return int(s[:-1]) * SIZE_UNITS[i]
            except ValueError:
                break
    raise ValueError("Invalid size specification.")


def pretty_duration(secs):
    formatters = [
        (100, "{:.0f}s"),
        (10, "{:2.1f}s"),
        (1, "{:1.2f}s"),
    ]

    for limit, formatter in formatters:
        if secs >= limit:
            return formatter.format(secs)
    # less than 1 sec
    return "{:.0f}ms".format(secs * 1000)


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp_with_milli(s):
    d = datetime.datetime.fromtimestamp(s)
    return d.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
