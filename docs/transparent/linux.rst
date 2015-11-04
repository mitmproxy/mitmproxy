.. _linux:

Linux
=====

On Linux, mitmproxy integrates with the iptables redirection mechanism to
achieve transparent mode.

 1. :ref:`Install the mitmproxy certificate on the test device <certinstall>`

 2. Enable IP forwarding:

    >>> sysctl -w net.ipv4.ip_forward=1

    You may also want to consider enabling this permanently in ``/etc/sysctl.conf``.

 3. If your target machine is on the same physical network and you configured it to use a custom
    gateway, disable ICMP redirects:

    >>> echo 0 | sudo tee /proc/sys/net/ipv4/conf/*/send_redirects

    You may also want to consider enabling this permanently in ``/etc/sysctl.conf``
    as demonstrated `here <https://unix.stackexchange.com/a/58081>`_.

 4. Create an iptables ruleset that redirects the desired traffic to the
    mitmproxy port. Details will differ according to your setup, but the
    ruleset should look something like this:

    .. code-block:: none

        iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
        iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080

 5. Fire up mitmproxy. You probably want a command like this:

    >>> mitmproxy -T --host

    The :option:`-T` flag turns on transparent mode, and the :option:`--host`
    argument tells mitmproxy to use the value of the Host header for URL display.

 6. Finally, configure your test device to use the host on which mitmproxy is
    running as the default gateway.


For a detailed walkthrough, have a look at the :ref:`transparent-dhcp` tutorial.
