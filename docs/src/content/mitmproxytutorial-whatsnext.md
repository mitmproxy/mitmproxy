---
title: "What's Next"
menu:
    mitmproxytutorial:
        weight: 5
---

# What's Next

Congratulations! You have successfully completed the mitmproxy tutorial. 🎉

We hope it was worthwhile and helped you getting up to speed with mitmproxy.
Is there anything you feel is missing? Or anything that is not clear? Please let us know in our <a href="https://github.com/mitmproxy/mitmproxy/issues/3142" target="_blank"> dedicated issue on GitHub</a>.

## Advanced usage

In this tutorial we have used mitmproxy to inspect requests initiated by curl.
You probably also want to inspect web traffic from your browser or some other tool.
To do so, you need to [configure mitmproxy as your client's proxy]({{< relref "overview-getting-started#configure-your-browser-or-device" >}}).

This tutorial is not meant as a replacement for our extensive docs.
mitmproxy has far more features than what we've shown you.
We recommend to read the documentation to get the full picture.

If you want to get in touch with the developers or other users, please use our [Slack channel](https://mitmproxy.slack.com).
If you want to contribute to mitmproxy or submit a bug report or other feedback, please do so on [GitHub](https://github.com/mitmproxy/).


### Customize Key bindings

Mitmproxy's key bindings can be customized to your needs in the
`~/.mitmproxy/keys.yaml` file. This file consists of a sequence of maps, with
the following keys:

* `key` (**mandatory**): The key to bind.
* `cmd` (**mandatory**): The command to execute when the key is pressed.
* `context`: A list of contexts in which the key should be bound. By default this is **global** (i.e. the key is bound everywhere). Valid contexts are `chooser`, `commands`, `dataviewer`, `eventlog`, `flowlist`, `flowview`, `global`, `grideditor`, `help`, `keybindings`, `options`.
* `help`: A help string for the binding which will be shown in the key binding browser.

#### Example

{{< example src="examples/keys.yaml" lang="yaml" >}}
