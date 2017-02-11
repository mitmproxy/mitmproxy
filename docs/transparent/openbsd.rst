.. _openbsd:

OpenBSD
=======

 1. :ref:`Install the mitmproxy certificate on the test device <certinstall>`

 2. Enable IP forwarding:

    >>> sudo sysctl -w net.inet.ip.forwarding=1

 3. Place the following two lines in **/etc/pf.conf**:

    .. code-block:: none

        mitm_if = "re2"
        pass in quick proto tcp from $mitm_if to port { 80, 443 } divert-to 127.0.0.1 port 8080

    These rules tell pf to divert all traffic from ``$mitm_if`` destined for
    port 80 or 443 to the local mitmproxy instance running on port 8080. You
    should replace ``$mitm_if`` value with the interface on which your test
    device will appear.

 4. Configure pf with the rules:

    >>> doas pfctl -f /etc/pf.conf

 5. And now enable it:

    >>> doas pfctl -e

 6. Fire up mitmproxy. You probably want a command like this:

    >>> mitmproxy -T --host

    The ``-T`` flag turns on transparent mode, and the ``--host``
    argument tells mitmproxy to use the value of the Host header for URL display.

 7. Finally, configure your test device to use the host on which mitmproxy is
    running as the default gateway.

.. note::

    Note that the **divert-to** rules in the pf.conf given above only apply to
    inbound traffic. **This means that they will NOT redirect traffic coming
    from the box running pf itself.** We can't distinguish between an outbound
    connection from a non-mitmproxy app, and an outbound connection from
    mitmproxy itself - if you want to intercept your traffic, you should use an
    external host to run mitmproxy. Nonetheless, pf is flexible to cater for a
    range of creative possibilities, like intercepting traffic emanating from
    VMs.  See the **pf.conf** man page for more.

.. _pf: http://man.openbsd.org/OpenBSD-current/man5/pf.conf.5
