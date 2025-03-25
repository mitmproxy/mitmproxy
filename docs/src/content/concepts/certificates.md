---
title: "Certificates"
weight: 3
aliases:
  - /concepts-certificates/
---

# About Certificates

Mitmproxy can decrypt encrypted traffic on the fly, as long as the client trusts
mitmproxy's built-in certificate authority. Usually this means that the mitmproxy CA
certificate has to be installed on the client device.

## Quick Setup

By far the easiest way to install the mitmproxy CA certificate is to use the
built-in certificate installation app. To do this, start mitmproxy and
configure your target device with the correct proxy settings. Now start a
browser on the device, and visit the magic domain [mitm.it](http://mitm.it/). You should see
something like this:

{{< figure src="/certinstall-webapp.png" class="has-border" >}}

Click on the relevant icon, follow the setup instructions for the platform
you're on and you are good to go.

## The mitmproxy certificate authority

The first time mitmproxy is run, it creates the keys for a certificate
authority (CA) in the config directory (`~/.mitmproxy` by default).
This CA is used for on-the-fly generation of dummy certificates for each visited website.
Since your browser won't trust the mitmproxy CA out of the box, you will either need to click through a TLS certificate
warning on every domain, or install the CA certificate once so that it is trusted.

The following files are created:

| Filename              | Contents                                                                             |
| --------------------- | ------------------------------------------------------------------------------------ |
| mitmproxy-ca.pem      | The certificate **and the private key** in PEM format.                               |
| mitmproxy-ca-cert.pem | The certificate in PEM format. Use this to distribute on most non-Windows platforms. |
| mitmproxy-ca-cert.p12 | The certificate in PKCS12 format. For use on Windows.                                |
| mitmproxy-ca-cert.cer | Same file as .pem, but with an extension expected by some Android devices.           |

For security reasons, the mitmproxy CA is generated uniquely on the first start and
is not shared between mitmproxy installations on different devices. This makes sure
that other mitmproxy users cannot intercept your traffic.

### Installing the mitmproxy CA certificate manually

Sometimes using the [quick install app](#quick-setup) is not an option and you need to install the CA manually.
Below is a list of pointers to manual certificate installation
documentation for some common platforms. The mitmproxy CA cert is located in
`~/.mitmproxy` after it has been generated at the first start of mitmproxy.

- curl on the command line:  
  `curl --proxy 127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com/`
- wget on the command line:  
  `wget -e https_proxy=127.0.0.1:8080 --ca-certificate ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com/`
- [macOS](https://support.apple.com/guide/keychain-access/add-certificates-to-a-keychain-kyca2431/mac)
- [macOS (automated)](https://www.dssw.co.uk/reference/security.html):
  `sudo security add-trusted-cert -d -p ssl -p basic -k /Library/Keychains/System.keychain ~/.mitmproxy/mitmproxy-ca-cert.pem`
- [Ubuntu/Debian]( https://askubuntu.com/questions/73287/how-do-i-install-a-root-certificate/94861#94861)
- [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/using-shared-system-certificates/#proc_adding-new-certificates)
- [Arch Linux](https://wiki.archlinux.org/title/Transport_Layer_Security#Add_a_certificate_to_a_trust_store)
- [Mozilla Firefox](https://wiki.mozilla.org/MozillaRootCertificate#Mozilla_Firefox)
- [Chrome on Linux](https://stackoverflow.com/a/15076602/198996)
- [iOS](http://jasdev.me/intercepting-ios-traffic)  
  On recent iOS versions you also need to enable full trust for the mitmproxy
  root certificate:
    1. Go to Settings > General > About > Certificate Trust Settings.
    2. Under "Enable full trust for root certificates", turn on trust for
       the mitmproxy certificate.
- iOS Simulator
  1. Ensure the macOS machine running the emulator is configured to use mitmproxy in its network settings.
  2. Open Safari on the emulator and visit `mitm.it` to download the iOS certificate.
  3. Navigate to Settings > General > VPN & Device Management to install the certificate.
  4. Go to Settings > About > Certificate Trust Settings and enable trust for the installed root certificate.
- [Java](https://docs.oracle.com/cd/E19906-01/820-4916/geygn/index.html):  
  `sudo keytool -importcert -alias mitmproxy -storepass changeit -keystore $JAVA_HOME/lib/security/cacerts -trustcacerts -file ~/.mitmproxy/mitmproxy-ca-cert.pem`
- [Android/Android Simulator](http://wiki.cacert.org/FAQ/ImportRootCert#Android_Phones_.26_Tablets)
- [Windows](https://web.archive.org/web/20160612045445/http://windows.microsoft.com/en-ca/windows/import-export-certificates-private-keys#1TC=windows-7)
- [Windows (automated)](https://technet.microsoft.com/en-us/library/cc732443.aspx):  
  `certutil -addstore root mitmproxy-ca-cert.cer`

### Upstream Certificate Sniffing

When mitmproxy receives a request to establish TLS (in the form of a ClientHello message), it puts the client on hold
and first makes a connection to the upstream server to "sniff" the contents of its TLS certificate.
The information gained -- Common Name, Organization, Subject Alternative Names -- is then used to generate a new
interception certificate on-the-fly, signed by the mitmproxy CA. Mitmproxy then returns to the client and continues
the handshake with the newly-forged certificate.

Upstream cert sniffing is on by default, and can optionally be disabled by turning the `upstream_cert` option off.

### Certificate Pinning

Some applications employ [Certificate
Pinning](https://en.wikipedia.org/wiki/HTTP_Public_Key_Pinning) to prevent
man-in-the-middle attacks. This means that **mitmproxy's**
certificates will not be accepted by these applications without modifying them.
If the contents of these connections are not important, it is recommended to use
the [ignore_hosts]({{< relref "/howto/ignore-domains">}}) feature to prevent
**mitmproxy** from intercepting traffic to these specific
domains. If you want to intercept the pinned connections, you need to patch the
application manually. For Android and (jailbroken) iOS devices, various tools
exist to accomplish this:

 - [apk-mitm](https://github.com/shroudedcode/apk-mitm) is a CLI application that automatically removes certificate
   pinning from Android APK files.
 - [objection](https://github.com/sensepost/objection) is a runtime mobile exploration toolkit powered by Frida,
   which supports certificate pinning bypasses on iOS and Android.
 - [ssl-kill-switch2](https://github.com/nabla-c0d3/ssl-kill-switch2) is a blackbox tool to disable certificate pinning
   within iOS and macOS applications.
 - [android-unpinner](https://github.com/mitmproxy/android-unpinner) modifies Android APKs to inject Frida and HTTP Toolkit's unpinning scripts.

*Please propose other useful tools using the "Edit on GitHub" button on the top right of this page.*

## Using a custom server certificate

You can use your own (leaf) certificate by passing the `--certs
[domain=]path_to_certificate` option to mitmproxy. Mitmproxy then uses the
provided certificate for interception of the specified domain instead of
generating a certificate signed by its own CA.

The certificate file is expected to be in the PEM format. You can include
intermediary certificates right below your leaf certificate, so that your PEM
file roughly looks like this:

    -----BEGIN PRIVATE KEY-----
    <private key>
    -----END PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    <cert>
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    <intermediary cert (optional)>
    -----END CERTIFICATE-----

For example, you can generate a certificate in this format using these
instructions:

```bash
openssl genrsa -out cert.key 2048
# (Specify the mitm domain as Common Name, e.g. \*.google.com)
openssl req -new -x509 -key cert.key -out cert.crt
cat cert.key cert.crt > cert.pem
```

Now, you can run mitmproxy with the generated certificate:

**For all domain names**

```bash
mitmproxy --certs *=cert.pem
```

**For specific domain names**

```bash
mitmproxy --certs *.example.com=cert.pem
```

**Note:** `*.example.com` is for all the subdomains. You can also use
`www.example.com` for a particular subdomain.

## Using a custom certificate authority

By default, mitmproxy will use `~/.mitmproxy/mitmproxy-ca.pem` as the
certificate authority to generate certificates for all domains for which
no custom certificate is provided (see above). You can use your own
certificate authority by passing the `--set confdir=DIRECTORY` option to
mitmproxy. Mitmproxy will then look for `mitmproxy-ca.pem` in the
specified directory. If no such file exists, it will be generated
automatically.

The `mitmproxy-ca.pem` certificate file has to look roughly like this:

    -----BEGIN PRIVATE KEY-----
    <private key>
    -----END PRIVATE KEY-----
    -----BEGIN CERTIFICATE-----
    <cert>
    -----END CERTIFICATE-----

When looking at the certificate with
`openssl x509 -noout -text -in ~/.mitmproxy/mitmproxy-ca.pem`
it should have at least the following X509v3 extensions so mitmproxy can
use it to generate certificates:

    X509v3 extensions:
        X509v3 Key Usage: critical
            Certificate Sign
        X509v3 Basic Constraints: critical
            CA:TRUE

For example, when using OpenSSL, you can create a CA authority as follows:

```shell
openssl req -x509 -new -nodes -key ca.key -sha256 -out ca.crt -addext keyUsage=critical,keyCertSign
cat ca.key ca.crt > mitmproxy-ca.pem
```

## Mutual TLS (mTLS) and client certificates

TLS is typically used in a way where the client verifies the server's identity
using the server's certificate during the handshake, but the server does not
verify the client's identity using the TLS protocol. Instead, the client 
transmits cookies or other access tokens over the established secure channel to
authenticate itself.

Mutual TLS (mTLS) is a mode where the server verifies the client's identity
not using cookies or access tokens, but using a certificate presented by the
client during the TLS handshake. With mTLS, both client and server use a 
certificate to authenticate each other.

If a server wants to verify the clients identity using mTLS, it sends an 
additional `CertificateRequest` message to the client during the handshake. The
client then provides its certificate and proves ownership of the private key 
with a matching signature. This part works just like server authentication, only
the other way around.

### mTLS between mitmproxy and upstream server

You can use a client certificate by passing the `--set client_certs=DIRECTORY|FILE`
option to mitmproxy. Using a directory allows certs to be selected based on
hostname, while using a filename allows a single specific certificate to be used
for all TLS connections. Certificate files must be in the PEM format and should
contain both the unencrypted private key and the certificate.

You can specify a directory to `--set client_certs=DIRECTORY`, in which case the matching
certificate is looked up by filename. So, if you visit example.org, mitmproxy
looks for a file named `example.org.pem` in the specified directory and uses
this as the client cert.

### mTLS between client and mitmproxy

By default, mitmproxy does not send the `CertificateRequest` TLS handshake
message to connecting clients. This is because it trips up some clients that do
not expect a certificate request (most famously old Android versions). However,
there are other clients -- in particular in the MQTT / IoT environment -- that 
do expect a certificate request and will otherwise fail the TLS handshake.

To instruct mitmproxy to request a client certificate from the connecting
client, you can pass the `--set request_client_cert=True` option. This will
generate a `CertificateRequest` TLS handshake message and (if successful)
establish an mTLS connection. This option only requests a certificate from the
client, it does not validate the presented identity in any way. For the purposes
of testing and developing client and server software, this is typically not an
issue. If you operate mitmproxy in an environment where untrusted clients might
connect, you need to safeguard against them.

The `request_client_cert` option is typically paired with `client_certs` like so:

```bash
mitmproxy --set request_client_cert=True --set client_certs=client-cert.pem
```
