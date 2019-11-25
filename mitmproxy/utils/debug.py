import gc
import os
import platform
import signal
import sys
import threading
import traceback

from OpenSSL import SSL

from mitmproxy import version


def dump_system_info():
    mitmproxy_version = version.get_dev_version()

    data = [
        "Mitmproxy: {}".format(mitmproxy_version),
        "Python:    {}".format(platform.python_version()),
        "OpenSSL:   {}".format(SSL.SSLeay_version(SSL.SSLEAY_VERSION).decode()),
        "Platform:  {}".format(platform.platform()),
    ]
    return "\n".join(data)


def dump_info(signal=None, frame=None, file=sys.stdout, testing=False):  # pragma: no cover
    print("****************************************************", file=file)
    print("Summary", file=file)
    print("=======", file=file)

    try:
        import psutil
    except:
        print("(psutil not installed, skipping some debug info)", file=file)
    else:
        p = psutil.Process()
        print("num threads: ", p.num_threads(), file=file)
        if hasattr(p, "num_fds"):
            print("num fds: ", p.num_fds(), file=file)
        print("memory: ", p.memory_info(), file=file)

        print(file=file)
        print("Files", file=file)
        print("=====", file=file)
        for i in p.open_files():
            print(i, file=file)

        print(file=file)
        print("Connections", file=file)
        print("===========", file=file)
        for i in p.connections():
            print(i, file=file)

    print(file=file)
    print("Threads", file=file)
    print("=======", file=file)
    bthreads = []
    for i in threading.enumerate():
        if hasattr(i, "_threadinfo"):
            bthreads.append(i)
        else:
            print(i.name, file=file)
    bthreads.sort(key=lambda x: x._thread_started)
    for i in bthreads:
        print(i._threadinfo(), file=file)

    print(file=file)
    print("Memory", file=file)
    print("=======", file=file)
    gc.collect()
    d = {}
    for i in gc.get_objects():
        t = str(type(i))
        if "mitmproxy" in t:
            d[t] = d.setdefault(t, 0) + 1
    itms = list(d.items())
    itms.sort(key=lambda x: x[1])
    for i in itms[-20:]:
        print(i[1], i[0], file=file)
    print("****************************************************", file=file)

    if not testing:
        sys.exit(1)


def dump_stacks(signal=None, frame=None, file=sys.stdout, testing=False):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append(
            "\n# Thread: %s(%d)" % (
                id2name.get(threadId, ""), threadId
            )
        )
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print("\n".join(code), file=file)
    if not testing:  # pragma: no cover
        sys.exit(1)


def register_info_dumpers():
    if os.name != "nt":  # pragma: windows no cover
        signal.signal(signal.SIGUSR1, dump_info)
        signal.signal(signal.SIGUSR2, dump_stacks)
