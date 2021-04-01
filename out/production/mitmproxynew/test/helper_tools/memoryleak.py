import gc
import threading
from pympler import muppy, refbrowser
from OpenSSL import SSL
# import os
# os.environ["TK_LIBRARY"] = r"C:\Python27\tcl\tcl8.5"
# os.environ["TCL_LIBRARY"] = r"C:\Python27\tcl\tcl8.5"

# Also noteworthy: guppy, objgraph

step = 0
__memory_locals__ = True


def str_fun(obj):
    if isinstance(obj, dict):
        if "__memory_locals__" in obj:
            return "(-locals-)"
        if "self" in obj and isinstance(obj["self"], refbrowser.InteractiveBrowser):
            return "(-browser-)"
    return str(id(obj)) + ": " + str(obj)[:100].replace("\r\n", "\\r\\n").replace("\n", "\\n")


def request(ctx, flow):
    global step, ssl
    print("==========")
    print(f"GC: {gc.collect()}")
    print(f"Threads: {threading.active_count()}")

    step += 1
    if step == 1:
        all_objects = muppy.get_objects()
        ssl = muppy.filter(all_objects, SSL.Connection)[0]
    if step == 2:
        ib = refbrowser.InteractiveBrowser(ssl, 2, str_fun, repeat=False)
        del ssl  # do this to unpollute view
        ib.main(True)
        # print("\r\n".join(str(x)[:100] for x in gc.get_referrers(ssl)))
