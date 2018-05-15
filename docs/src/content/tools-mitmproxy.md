---
title: "mitmproxy"
menu: "tools"
menu:
    tools:
        weight: 1
---

## mitmproxy

{{< figure src="/screenshots/mitmproxy.png" >}}

**mitmproxy** is a console tool that allows interactive examination and
modification of HTTP traffic. It differs from mitmdump in that all flows are
kept in memory, which means that it's intended for taking and manipulating
small-ish samples. Use the `?` shortcut key to view, context-sensitive
documentation from any **mitmproxy** screen.

### Key binding configuration

Mitmproxy's key bindings can be customized through in the
`~/.mitmproxy/keys.yaml` file. This file consists of a sequence of maps, with
the following keys:

* `key` (**mandatory**): The key to bind.
* `cmd` (**mandatory**): The command to execute when the key is pressed.
* `context`: A list of contexts in which the key should be bound. By default this is **global** (i.e. the key is bound everywhere). Valid contexts are `chooser`, `commands`, `dataviewer`, `eventlog`, `flowlist`, `flowview`, `global`, `grideditor`, `help`, `keybindings`, `options`.
* `help`: A help string for the binding which will be shown in the key binding browser.

#### Example

{{< example src="examples/keys.yaml" lang="yaml" >}}




