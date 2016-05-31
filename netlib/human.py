SIZE_UNITS = dict(
    b=1024 ** 0,
    k=1024 ** 1,
    m=1024 ** 2,
    g=1024 ** 3,
    t=1024 ** 4,
)


def pretty_size(size):
    suffixes = [
        ("B", 2 ** 10),
        ("kB", 2 ** 20),
        ("MB", 2 ** 30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size / float(lim / 2 ** 10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


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
