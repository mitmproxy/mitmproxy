---
title: "Client replay"
menu:
    tutes:
        weight: 1
---

# Client playback: a 30 second example

My local cafe is serviced by a rickety and unreliable wireless network,
generously sponsored with ratepayers' money by our city council. After
connecting, you are redirected to an SSL-protected page that prompts you for a
username and password. Once you've entered your details, you are free to enjoy
the intermittent dropouts, treacle-like speeds and incorrectly configured
transparent proxy.

I tend to automate this kind of thing at the first opportunity, on the theory
that time spent now will be more than made up in the long run. In this case, I
might use [Firebug](https://getfirebug.com/) to ferret out the form post
parameters and target URL, then fire up an editor to write a little script using
Python's [urllib](https://docs.python.org/library/urllib.html) to simulate a
submission. That's a lot of futzing about. With mitmproxy we can do the job in
literally 30 seconds, without having to worry about any of the details. Here's
how.

## 1. Run mitmdump to record our HTTP conversation to a file.

{{< highlight bash  >}}
mitmdump -w wireless-login
{{< / highlight >}}

## 2. Point your browser at the mitmdump instance.

I use a tiny Firefox addon called [Toggle
Proxy](https://addons.mozilla.org/en-us/firefox/addon/toggle-proxy-51740/) to
switch quickly to and from mitmproxy. I'm assuming you've already [configured
your browser with mitmproxy's SSL certificate authority]({{< relref
"concepts-certificates" >}}).

## 3. Log in as usual

And that's it\! You now have a serialised version of the login process
in the file wireless-login, and you can replay it at any time like this:

{{< highlight bash  >}}
mitmdump -c wireless-login
{{< / highlight >}}

## Embellishments

We're really done at this point, but there are a couple of embellishments we
could make if we wanted. I use [wicd](https://launchpad.net/wicd) to
automatically join wireless networks I frequent, and it lets me specify a
command to run after connecting. I used the client replay command above and
voila\! - totally hands-free wireless network startup.

We might also want to prune requests that download CSS, JS, images and so forth.
These add only a few moments to the time it takes to replay, but they're not
really needed and I somehow feel compelled to trim them anyway. So, we fire up
the mitmproxy console tool on our serialised conversation, like so:

{{< highlight bash  >}}
mitmproxy -r wireless-login
{{< / highlight >}}

We can now go through and manually delete (using the <span
data-role="kbd">d</span> keyboard shortcut) everything we want to trim. When
we're done, we use <span data-role="kbd">w</span> to save the conversation back
to the file.
