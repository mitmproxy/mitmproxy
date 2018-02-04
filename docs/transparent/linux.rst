.. _linux:

Linux
=====

On Linux, mitmproxy integrates with the iptables redirection mechanism to
achieve transparent mode.

 1. :ref:`Install the mitmproxy certificate on the test device <certinstall>`

 2. Enable IP forwarding:

    >>> sysctl -w net.ipv4.ip_forward=1
    >>> sysctl -w net.ipv6.conf.all.forwarding=1

    You may also want to consider enabling this permanently in ``/etc/sysctl.conf`` or newly created ``/etc/sysctl.d/mitmproxy.conf``, see `here <https://superuser.com/a/625852>`__.

 3. If your target machine is on the same physical network and you configured it to use a custom
    gateway, disable ICMP redirects:

    >>> sysctl -w net.ipv4.conf.all.accept_redirects=0
    >>> sysctl -w net.ipv6.conf.all.accept_redirects=0
    >>> sysctl -w net.ipv4.conf.all.send_redirects=0

    You may also want to consider enabling this permanently in ``/etc/sysctl.conf`` or a newly created ``/etc/sysctl.d/mitmproxy.conf``, see `here <https://superuser.com/a/625852>`__.

 4. Create an iptables ruleset that redirects the desired traffic to the
    mitmproxy port. Details will differ according to your setup, but the
    ruleset should look something like this:

    .. code-block:: none

        iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
        iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080
        ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
        ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080
        
    You may also want to consider enabling this permanently with the ``iptables-persistent`` package, see `here <http://www.microhowto.info/howto/make_the_configuration_of_iptables_persistent_on_debian.html>`__.

 5. Fire up mitmproxy. You probably want a command like this:

    >>> mitmproxy -T --host

    The ``-T`` flag turns on transparent mode, and the ``--host``
    argument tells mitmproxy to use the value of the Host header for URL display.

 6. Finally, configure your test device to use the host on which mitmproxy is
    running as the default gateway.


For a detailed walkthrough, have a look at the :ref:`transparent-dhcp` tutorial.
