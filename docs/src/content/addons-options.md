---
title: "Options"
menu:
    addons:
        weight: 3
---

# Options

At the heart of mitmproxy is a global options store, containing the settings
that determine the behaviour of both mitmproxy and its addons. Options can be
read from a configuration file, set on the command-line and changed
interactively by users on the fly.

All options are annotated with one of a set of supported types. Mitmproxy knows
how to serialise and deserialise these types, and has standard ways of
presenting typed values for editing in interactive programs. Attempting to set a
value with the wrong type will result in an error. This means that addon options
get full support throughout mitmproxy's toolchain simply by declaring a type.

## Simple example

{{< example src="examples/addons/options-simple.py" lang="py" >}}

The `load` event receives an instance of `mitmproxy.addonmanager.Loader`, which
allows addons declare options and commands. In this case, the addon adds a
single `addheader` option with type `bool`. Let's try this out by running the
script in mitmproxy console:

```bash
> mitmproxy -s ./examples/addons/options-simple.py
```

You can now use CURL to make a request through the proxy like this:

```bash
> env http_proxy=http://localhost:8080 curl -I http://google.com
```

If you run this request immediately, you'll notice that no count header is
added. This is because our default value for the option was `false`. Press `O`
to enter the options editor, and find the `addheader` option. You'll notice that
mitmproxy knows this is a boolean, and lets you toggle the value between true
and false. Set the value to `true`, and you should see a result something like
this:

```bash
> env http_proxy=http://localhost:8080 curl -I http://google.com
HTTP/1.1 301 Moved Permanently
Location: http://www.google.com/
Content-Length: 219
count: 1
```

When this addon is loaded, the `addheader` setting is available in the
persistent [YAML configuration file]({{< relref "concepts-options" >}}). You can
also over-ride the value directly from the command-line for any of the tools
using the `--set` flag:

```bash
mitmproxy -s ./examples/addons/options-simple.py --set addheader=true
```

## Handling configuration updates

Sometimes, simply testing the value of an option from an event is not
sufficient. Instead, we want to act immediately when an option is changed by the
user. This is what the `configure` event is for - when it is triggered, it
receives a set of changed options. An addon can check if an option is in this
set, and then read the value from the options object on the context.

One common use for this function is to check that an option is valid, and give
the user feedback if it's not. If an `exceptions.OptionsError` exception is
raised during configure, all the changes in the update are automatically rolled
back, and an error is displayed to the user. Let's see an example.

{{< example src="examples/addons/options-configure.py" lang="py" >}}

There are a few things to note here. First, the option we add uses
`typing.Optional`. This signals to mitmproxy that `None` is a valid value for
this option - that is, it can be unset. Second, the `configure` method is first
called with our default value (`None`), and then later with an updated value if
the option is changed. If we try to load the script with an incorrect value, we
now see an error:

```
> mitmdump -s ./examples/addons/options-configure.py --set addheader=1000
Loading script: ./examples/addons/options-configure.py
/Users/cortesi/mitmproxy/mitmproxy/venv/bin/mitmdump: addheader must be <= 100
```

## Supported Types

The following types are supported for options.

- Primitive types - `str`, `int`, `float`, `bool`.
- Optional values, annotated using `typing.Optional`.
- Sequences of values, annotated using `typing.Sequence`.
