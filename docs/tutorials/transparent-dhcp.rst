.. _transparent-dhcp:

Transparently proxify virtual machines
======================================

This walkthrough illustrates how to set up transparent proxying with mitmproxy.
We use VirtualBox VMs with an Ubuntu proxy machine in this example,
but the general *Internet <--> Proxy VM <--> (Virtual) Internal Network* setup can be applied to
other setups.

1. Configure Proxy VM
---------------------

On the proxy machine, **eth0** is connected to the internet. **eth1** is connected to the internal
network that will be proxified and configured to use a static ip (192.168.3.1).

VirtualBox configuration
^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: transparent-dhcp/step1_vbox_eth0.png

.. image:: transparent-dhcp/step1_vbox_eth1.png

VM Network Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: transparent-dhcp/step1_proxy.png
    :align: center

2. Configure DHCP and DNS
-------------------------

We use dnsmasq to provide DHCP and DNS in our internal network.
Dnsmasq is a lightweight server designed to provide DNS (and optionally
DHCP and TFTP) services to a small-scale network.

-   Before we get to that, we need to fix some Ubuntu quirks:
    **Ubuntu >12.04** runs an internal dnsmasq instance (listening on loopback only) by default
    `[1] <https://www.stgraber.org/2012/02/24/dns-in-ubuntu-12-04/>`_. For our use case, this needs
    to be disabled by changing ``dns=dnsmasq`` to ``#dns=dnsmasq`` in
    **/etc/NetworkManager/NetworkManager.conf** and running

    >>> sudo restart network-manager

    afterwards.
-   Now, dnsmasq can be be installed and configured:

    >>> sudo apt-get install dnsmasq

    Replace **/etc/dnsmasq.conf** with the following configuration:

    .. code-block:: none

        # Listen for DNS requests on the internal network
        interface=eth1
        # Act as a DHCP server, assign IP addresses to clients
        dhcp-range=192.168.3.10,192.168.3.100,96h
        # Broadcast gateway and dns server information
        dhcp-option=option:router,192.168.3.1
        dhcp-option=option:dns-server,192.168.3.1

    Apply changes:

    >>> sudo service dnsmasq restart

    Your **proxied machine** in the internal virtual network should now receive an IP address via DHCP:

    .. image:: transparent-dhcp/step2_proxied_vm.png

3. Redirect traffic to mitmproxy
------------------------------------------

To redirect traffic to mitmproxy, we need to add two iptables rules:

.. code-block:: none

    iptables -t nat -A PREROUTING -i eth1 -p tcp --dport 80 -j REDIRECT --to-port 8080
    iptables -t nat -A PREROUTING -i eth1 -p tcp --dport 443 -j REDIRECT --to-port 8080

4. Run mitmproxy
----------------

Finally, we can run mitmproxy in transparent mode with

>>> mitmproxy -T

The proxied machine cannot to leak any data outside of HTTP or DNS requests.
If required, you can now :ref:`install the mitmproxy certificates on the proxied machine
<certinstall>`.
