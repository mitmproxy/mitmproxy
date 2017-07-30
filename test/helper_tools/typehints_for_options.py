import typing
from unittest import mock

from mitmproxy import proxy, options
from mitmproxy.tools import dump, console, web


def print_typehints(opts):
    for name, option in sorted(opts.items()):
        print(
            # For Python 3.6, we can just use "{}: {}".
            "{} = None  # type: {}".format(
                name,
                {
                    int: "int",
                    str: "str",
                    bool: "bool",
                    typing.Optional[str]: "Optional[str]",
                    typing.Sequence[str]: "Sequence[str]"
                }[option.typespec]
            )
        )


if __name__ == "__main__":
    opts = options.Options()
    server = proxy.server.DummyServer(None)

    # initialize with all three tools here to capture tool-specific options defined in addons.
    dump.DumpMaster(opts, server)
    with mock.patch("sys.stdout.isatty", lambda: True):
        console.master.ConsoleMaster(opts, server)
    web.master.WebMaster(opts, server)
    print_typehints(opts)
