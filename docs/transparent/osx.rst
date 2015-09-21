.. _osx:

OSX
===

OSX Lion integrated the pf_ packet filter from the OpenBSD project,
which mitmproxy uses to implement transparent mode on OSX.
Note that this means we don't support transparent mode for earlier versions of OSX.

 1. :ref:`Install the mitmproxy certificate on the test device <certinstall>`

 2. Enable IP forwarding:

    >>> sudo sysctl -w net.inet.ip.forwarding=1

 3. Place the following two lines in a file called, say, **pf.conf**:

    .. code-block:: none

        rdr on en2 inet proto tcp to any port 80 -> 127.0.0.1 port 8080
        rdr on en2 inet proto tcp to any port 443 -> 127.0.0.1 port 8080

    These rules tell pf to redirect all traffic destined for port 80 or 443
    to the local mitmproxy instance running on port 8080. You should
    replace ``en2`` with the interface on which your test device will appear.

 4. Configure pf with the rules:

    >>> sudo pfctl -f pf.conf

 5. And now enable it:

    >>> sudo pfctl -e

 6. Configure sudoers to allow mitmproxy to access pfctl. Edit the file
    **/etc/sudoers** on your system as root. Add the following line to the end
    of the file:

    .. code-block:: none

        ALL ALL=NOPASSWD: /sbin/pfctl -s state

    Note that this allows any user on the system to run the command
    ``/sbin/pfctl -s state`` as root without a password. This only allows
    inspection of the state table, so should not be an undue security risk. If
    you're special feel free to tighten the restriction up to the user running
    mitmproxy.

 7. Fire up mitmproxy. You probably want a command like this:

    >>> mitmproxy -T --host

    The :option:`-T` flag turns on transparent mode, and the :option:`--host`
    argument tells mitmproxy to use the value of the Host header for URL display.

 8. Finally, configure your test device to use the host on which mitmproxy is
    running as the default gateway.

.. note::

    Note that the **rdr** rules in the pf.conf given above only apply to inbound
    traffic. **This means that they will NOT redirect traffic coming from the box
    running pf itself.** We can't distinguish between an outbound connection from a
    non-mitmproxy app, and an outbound connection from mitmproxy itself - if you
    want to intercept your OSX traffic, you should use an external host to run
    mitmproxy. None the less, pf is flexible to cater for a range of creative
    possibilities, like intercepting traffic emanating from VMs.  See the
    **pf.conf** man page for more.

.. _pf: https://en.wikipedia.org/wiki/PF_\(firewall\)
