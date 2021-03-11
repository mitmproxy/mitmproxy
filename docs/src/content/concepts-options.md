---
title: "Options"
menu:
    concepts:
        weight: 5
---

# Options

The mitmproxy tools share a common [YAML](http://yaml.org/) configuration file
located at `~/.mitmproxy/config.yaml`. This file controls **options** - typed
values that determine the behaviour of mitmproxy. The options mechanism is very
comprehensive - in fact, options control all of mitmproxy's runtime behaviour.
Most command-line flags are simply aliases for underlying options, and
interactive settings changes made in **mitmproxy** and **mitmweb** just change
values in our runtime options store. This means that almost any facet of
mitmproxy's behaviour can be controlled through options.

The canonical reference for options is the `--options` flag, which is exposed by
each of the mitmproxy tools. Passing this flag will dump an annotated YAML
configuration to console, which includes all options and their default values.

The options mechanism is extensible - third-party addons can define options that
are treated exactly like mitmproxy's own. This means that addons can also be
configured through the central configuration file, and their options will appear
in the options editors in interactive tools.

## Tools

Both **mitmproxy** and **mitmweb** have built-in editors that let you view and
manipulate the complete configuration state of mitmproxy. Values you change
interactively have immediate effect in the running instance, and can be made
persistent by saving the settings out to a YAML configuration file (please see
the specific tool's interactive help for details on how to do this).

For all tools, options can be set directly by name using the `--set`
command-line option. Please see the command-line help (`--help`) for usage.

## Available Options

This list might not reflect what is actually available in your current mitmproxy
environment. For an up-to-date list please use the `--options` flag for each of
the mitmproxy tools.

{{< readfile file="/generated/options.html" >}}
