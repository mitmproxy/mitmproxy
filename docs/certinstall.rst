.. _certinstall:

About Certificates
==================

Introduction
------------

Mitmproxy can decrypt encrypted traffic on the fly, as long as the client
trusts its built-in certificate authority. Usually this means that the
mitmproxy CA certificates have to be installed on the client device.

Quick Setup
-----------

By far the easiest way to install the mitmproxy certificates is to use the
built-in certificate installation app. To do this, just start mitmproxy and
configure your target device with the correct proxy settings. Now start a
browser on the device, and visit the magic domain **mitm.it**. You should see
something like this:

.. image:: certinstall-webapp.png

Click on the relevant icon, follow the setup instructions for the platform
you're on and you are good to go.


Installing the mitmproxy CA certificate manually
------------------------------------------------

Sometimes using the quick install app is not an option - Java or the iOS
Simulator spring to mind - or you just need to do it manually for some other
reason. Below is a list of pointers to manual certificate installation
documentation for some common platforms.

The mitmproxy CA cert is located in ``~/.mitmproxy`` after it has been generated at the first
start of mitmproxy.


iOS
^^^

http://kb.mit.edu/confluence/pages/viewpage.action?pageId=152600377

iOS Simulator
^^^^^^^^^^^^^

See https://github.com/ADVTOOLS/ADVTrustStore#how-to-use-advtruststore

Java
^^^^

See http://docs.oracle.com/cd/E19906-01/820-4916/geygn/index.html

Android/Android Simulator
^^^^^^^^^^^^^^^^^^^^^^^^^

See http://wiki.cacert.org/FAQ/ImportRootCert#Android_Phones_.26_Tablets

Windows
^^^^^^^

See http://windows.microsoft.com/en-ca/windows/import-export-certificates-private-keys#1TC=windows-7

Windows (automated)
^^^^^^^^^^^^^^^^^^^

>>> certutil.exe -importpfx mitmproxy-ca-cert.p12

See also: https://technet.microsoft.com/en-us/library/cc732443.aspx

Mac OS X
^^^^^^^^

See https://support.apple.com/kb/PH7297?locale=en_US

Ubuntu/Debian
^^^^^^^^^^^^^

See http://askubuntu.com/questions/73287/how-do-i-install-a-root-certificate/94861#94861

Mozilla Firefox
^^^^^^^^^^^^^^^

See https://wiki.mozilla.org/MozillaRootCertificate#Mozilla_Firefox

Chrome on Linux
^^^^^^^^^^^^^^^

See https://code.google.com/p/chromium/wiki/LinuxCertManagement


The mitmproxy certificate authority
-----------------------------------

The first time **mitmproxy** or **mitmdump** is run, the mitmproxy Certificate
Authority (CA) is created in the config directory (``~/.mitmproxy`` by default).
This CA is used for on-the-fly generation of dummy certificates for each of the
SSL sites that your client visits. Since your browser won't trust the
mitmproxy CA out of the box, you will see an SSL certificate warning every
time you visit a new SSL domain through mitmproxy. When you are testing a
single site through a browser, just accepting the bogus SSL cert manually is
not too much trouble, but there are a many circumstances where you will want to
configure your testing system or browser to trust the mitmproxy CA as a
signing root authority. For security reasons, the mitmproxy CA is generated uniquely on the first start and is not shared between mitmproxy installations on different devices.

Certificate Pinning
^^^^^^^^^^^^^^^^^^^

Some applications employ `Certificate Pinning`_ to prevent man-in-the-middle attacks.
This means that **mitmproxy** and **mitmdump's** certificates will not be
accepted by these applications without modifying them. It is recommended to use the
:ref:`passthrough` feature in order to prevent **mitmproxy** and **mitmdump** from intercepting
traffic to these specific domains. If you want to intercept the pinned connections, you need to patch the application manually. For Android and (jailbroken) iOS devices, various tools exist to accomplish this.


CA and cert files
-----------------

The files created by mitmproxy in the .mitmproxy directory are as follows:

===================== ==========================================================================
mitmproxy-ca.pem      The certificate **and the private key** in PEM format.
mitmproxy-ca-cert.pem The certificate in PEM format.
                      Use this to distribute on most non-Windows platforms.
mitmproxy-ca-cert.p12 The certificate in PKCS12 format. For use on Windows.
mitmproxy-ca-cert.cer Same file as .pem, but with an extension expected by some Android devices.
===================== ==========================================================================

Using a custom certificate
--------------------------

You can use your own certificate by passing the ``--cert`` option to
mitmproxy. Mitmproxy then uses the provided certificate for interception of the
specified domains instead of generating a certificate signed by its own CA.

The certificate file is expected to be in the PEM format.  You can include
intermediary certificates right below your leaf certificate, so that you PEM
file roughly looks like this:

.. code-block:: none

    -----BEGIN PRIVATE KEY-----
    <private key>
    -----END PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    <cert>
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    <intermediary cert (optional)>
    -----END CERTIFICATE-----


For example, you can generate a certificate in this format using these instructions:


>>> openssl genrsa -out cert.key 2048
>>> openssl req -new -x509 -key cert.key -out cert.crt
    (Specify the mitm domain as Common Name, e.g. *.google.com)
>>> cat cert.key cert.crt > cert.pem
>>> mitmproxy --cert=cert.pem


Using a custom certificate authority
------------------------------------

By default, mitmproxy will use ``~/.mitmproxy/mitmproxy-ca.pem`` as
the certificate authority to generate certificates for all domains for which no
custom certificate is provided (see above). You can use your own certificate
authority by passing the ``--cadir DIRECTORY`` option to mitmproxy. Mitmproxy
will then look for ``mitmproxy-ca.pem`` in the specified directory. If
no such file exists, it will be generated automatically.


Using a client side certificate
-------------------------------

You can use a client certificate by passing the ``--client-certs DIRECTORY|FILE``
option to mitmproxy. Using a directory allows certs to be selected based on
hostname, while using a filename allows a single specific certificate to be used for
all SSL connections. Certificate files must be in the PEM format and should
contain both the unencrypted private key and the certificate.

Multiple certs by Hostname
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you've specified a directory to ``--client-certs``, then the following
behavior will be taken:

If you visit example.org, mitmproxy looks for a file named ``example.org.pem`` in the specified
directory and uses this as the client cert.



.. _Certificate Pinning: http://security.stackexchange.com/questions/29988/what-is-certificate-pinning/