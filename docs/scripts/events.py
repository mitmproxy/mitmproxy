#!/usr/bin/env python3
import inspect
import textwrap
from typing import List, Type

import mitmproxy.addons.next_layer  # noqa
from mitmproxy import hooks, log, addonmanager
from mitmproxy.proxy import server_hooks, layer
from mitmproxy.proxy.layers import http, tcp, tls, websocket

known = set()


def category(name: str, hooks: List[Type[hooks.Hook]]) -> None:
    print(f"### {name} Events")
    print("```python")

    all_params = [
        list(inspect.signature(hook.__init__).parameters.values())[1:]
        for hook in hooks
    ]

    # slightly overengineered, but this was fun to write.  ¯\_(ツ)_/¯
    imports = set()
    types = set()
    for params in all_params:
        for param in params:
            try:
                mod = inspect.getmodule(param.annotation).__name__
                if mod == "typing":
                    # this is ugly, but can be removed once we are on Python 3.9+ only
                    imports.add(inspect.getmodule(param.annotation.__args__[0]).__name__)
                    types.add(param.annotation._name)
                else:
                    imports.add(mod)
            except AttributeError:
                raise ValueError(f"Missing type annotation: {params}")
    imports.discard("builtins")
    if types:
        print(f"from typing import {', '.join(sorted(types))}")
    print("from mitmproxy import ctx")
    for imp in sorted(imports):
        print(f"import {imp}")
    print()

    first = True
    for hook, params in zip(hooks, all_params):
        if first:
            first = False
        else:
            print()
        if hook.name in known:
            raise RuntimeError(f"Already documented: {hook}")
        known.add(hook.name)
        doc = inspect.getdoc(hook)
        print(f"def {hook.name}({', '.join(str(p) for p in params)}):")
        print(textwrap.indent(f'"""\n{doc}\n"""', "    "))
        if params:
            print(f'    ctx.log(f"{hook.name}: {" ".join("{" + p.name + "=}" for p in params)}")')
        else:
            print(f'    ctx.log("{hook.name}")')
    print("```")


category(
    "Lifecycle",
    [
        addonmanager.LoadHook,
        hooks.RunningHook,
        hooks.ConfigureHook,
        hooks.DoneHook,
    ]
)

category(
    "Connection",
    [
        server_hooks.ClientConnectedHook,
        server_hooks.ClientDisconnectedHook,
        server_hooks.ServerConnectHook,
        server_hooks.ServerConnectedHook,
        server_hooks.ServerDisconnectedHook,
    ]
)

category(
    "HTTP",
    [
        http.HttpRequestHeadersHook,
        http.HttpRequestHook,
        http.HttpResponseHeadersHook,
        http.HttpResponseHook,
        http.HttpErrorHook,
        http.HttpConnectHook,
    ]
)

category(
    "TCP",
    [
        tcp.TcpStartHook,
        tcp.TcpMessageHook,
        tcp.TcpEndHook,
        tcp.TcpErrorHook,
    ]
)

category(
    "TLS",
    [
        tls.TlsClienthelloHook,
        tls.TlsStartHook,
    ]
)

category(
    "WebSocket",
    [
        websocket.WebsocketStartHook,
        websocket.WebsocketMessageHook,
        websocket.WebsocketEndHook,
        websocket.WebsocketErrorHook,
    ]
)

category(
    "Advanced Lifecycle",
    [
        layer.NextLayerHook,
        hooks.UpdateHook,
        log.AddLogHook,
    ]
)

not_documented = set(hooks.all_hooks.keys()) - known
if not_documented:
    raise RuntimeError(f"Not documented: {not_documented}")

# print("<table class=\"table filtertable\"><tbody>")
# for i in flowfilter.help:
#    print("<tr><th>%s</th><td>%s</td></tr>" % i)
# print("</tbody></table>")
