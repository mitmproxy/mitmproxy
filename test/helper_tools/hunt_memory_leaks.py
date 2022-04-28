import collections
import gc
import os
import signal

from mitmproxy import flow


def load(loader):
    signal.signal(signal.SIGUSR1, debug1)
    signal.signal(signal.SIGUSR2, debug2)
    print(f"Debug signal registered. Run the following commands for diagnostics:")
    print()
    print(f"  kill -s USR1 {os.getpid()}")
    print(f"  kill -s USR2 {os.getpid()}")
    print()


def debug1(*_):
    print()
    print("Before GC")
    print("=======")
    print("gc.get_stats", gc.get_stats())
    print("gc.get_count", gc.get_count())
    print("gc.get_threshold", gc.get_threshold())

    gc.collect()

    print()
    print("After GC")
    print("=======")
    print("gc.get_stats", gc.get_stats())
    print("gc.get_count", gc.get_count())
    print("gc.get_threshold", gc.get_threshold())

    print()
    print("Memory")
    print("=======")
    for t, count in collections.Counter(
        [str(type(o)) for o in gc.get_objects()]
    ).most_common(50):
        print(count, t)


def debug2(*_):
    print()
    print("Flow References")
    print("=======")

    # gc.collect()

    objs = tuple(gc.get_objects())
    ignore = {id(objs)}  # noqa
    flows = 0
    for i in range(len(objs)):
        try:
            is_flow = isinstance(objs[i], flow.Flow)
        except Exception:
            continue
        if is_flow:
            flows += 1
            # print_refs(objs[i], ignore, set())
            # break
    del objs

    print(f"{flows} flows found.")


def print_refs(x, ignore: set, seen: set, depth: int = 0, max_depth: int = 10):
    if id(x) in ignore:
        return

    if id(x) in seen:
        print(
            "  " * depth
            + "↖ "
            + repr(str(x))[1:60]
            + f" (\x1b[31mseen\x1b[0m: {id(x):x})"
        )
        return
    else:
        if depth == 0:
            print("- " + repr(str(x))[1:60] + f" ({id(x):x})")
        else:
            print("  " * depth + "↖ " + repr(str(x))[1:60] + f" ({id(x):x})")
        seen.add(id(x))

    if depth == max_depth:
        return

    referrers = tuple(gc.get_referrers(x))
    ignore.add(id(referrers))
    for ref in referrers:
        print_refs(ref, ignore, seen, depth + 1, max_depth)
