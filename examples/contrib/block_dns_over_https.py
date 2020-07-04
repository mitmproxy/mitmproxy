"""
This module is for blocking DNS over HTTPS requests.

It loads a blocklist of IPs and hostnames that are known to serve DNS over HTTPS requests.
It also uses headers, query params, and paths to detect DoH (and block it)
"""
from typing import List

from mitmproxy import ctx

# known DoH providers' hostnames and IP addresses to block
default_blocklist: dict = {
    "hostnames": [
        "dns.adguard.com", "dns-family.adguard.com", "dns.google", "cloudflare-dns.com",
        "mozilla.cloudflare-dns.com", "security.cloudflare-dns.com", "family.cloudflare-dns.com",
        "dns.quad9.net", "dns9.quad9.net", "dns10.quad9.net", "dns11.quad9.net", "doh.opendns.com",
        "doh.familyshield.opendns.com", "doh.cleanbrowsing.org", "doh.xfinity.com", "dohdot.coxlab.net",
        "odvr.nic.cz", "doh.dnslify.com", "dns.nextdns.io", "dns.dnsoverhttps.net", "doh.crypto.sx",
        "doh.powerdns.org", "doh-fi.blahdns.com", "doh-jp.blahdns.com", "doh-de.blahdns.com",
        "doh.ffmuc.net", "dns.dns-over-https.com", "doh.securedns.eu", "dns.rubyfish.cn",
        "dns.containerpi.com", "dns.containerpi.com", "dns.containerpi.com", "doh-2.seby.io",
        "doh.seby.io", "commons.host", "doh.dnswarden.com", "doh.dnswarden.com", "doh.dnswarden.com",
        "dns-nyc.aaflalo.me", "dns.aaflalo.me", "doh.applied-privacy.net", "doh.captnemo.in",
        "doh.tiar.app", "doh.tiarap.org", "doh.dns.sb", "rdns.faelix.net", "doh.li", "doh.armadillodns.net",
        "jp.tiar.app", "jp.tiarap.org", "doh.42l.fr", "dns.hostux.net", "dns.hostux.net", "dns.aa.net.uk",
        "adblock.mydns.network", "ibksturm.synology.me", "jcdns.fun", "ibuki.cgnat.net", "dns.twnic.tw",
        "example.doh.blockerdns.com", "dns.digitale-gesellschaft.ch", "doh.libredns.gr",
        "doh.centraleu.pi-dns.com", "doh.northeu.pi-dns.com", "doh.westus.pi-dns.com",
        "doh.eastus.pi-dns.com", "dns.flatuslifir.is", "private.canadianshield.cira.ca",
        "protected.canadianshield.cira.ca", "family.canadianshield.cira.ca", "dns.google.com",
        "dns.google.com"
    ],
    "ips": [
        "104.16.248.249", "104.16.248.249", "104.16.249.249", "104.16.249.249", "104.18.2.55",
        "104.18.26.128", "104.18.27.128", "104.18.3.55", "104.18.44.204", "104.18.44.204",
        "104.18.45.204", "104.18.45.204", "104.182.57.196", "104.236.178.232", "104.24.122.53",
        "104.24.123.53", "104.28.0.106", "104.28.1.106", "104.31.90.138", "104.31.91.138",
        "115.159.131.230", "116.202.176.26", "116.203.115.192", "136.144.215.158", "139.59.48.222",
        "139.99.222.72", "146.112.41.2", "146.112.41.3", "146.185.167.43", "149.112.112.10",
        "149.112.112.11", "149.112.112.112", "149.112.112.9", "149.112.121.10", "149.112.121.20",
        "149.112.121.30", "149.112.122.10", "149.112.122.20", "149.112.122.30", "159.69.198.101",
        "168.235.81.167", "172.104.93.80", "172.65.3.223", "174.138.29.175", "174.68.248.77",
        "176.103.130.130", "176.103.130.131", "176.103.130.132", "176.103.130.134", "176.56.236.175",
        "178.62.214.105", "185.134.196.54", "185.134.197.54", "185.213.26.187", "185.216.27.142",
        "185.228.168.10", "185.228.168.168", "185.235.81.1", "185.26.126.37", "185.26.126.37",
        "185.43.135.1", "185.95.218.42", "185.95.218.43", "195.30.94.28", "2001:148f:fffe::1",
        "2001:19f0:7001:3259:5400:2ff:fe71:bc9", "2001:19f0:7001:5554:5400:2ff:fe57:3077",
        "2001:19f0:7001:5554:5400:2ff:fe57:3077", "2001:19f0:7001:5554:5400:2ff:fe57:3077",
        "2001:4860:4860::8844", "2001:4860:4860::8888",
        "2001:4b98:dc2:43:216:3eff:fe86:1d28", "2001:558:fe21:6b:96:113:151:149",
        "2001:608:a01::3", "2001:678:888:69:c45d:2738:c3f2:1878", "2001:8b0::2022", "2001:8b0::2023",
        "2001:c50:ffff:1:101:101:101:101", "210.17.9.228", "217.169.20.22", "217.169.20.23",
        "2400:6180:0:d0::5f73:4001", "2400:8902::f03c:91ff:feda:c514", "2604:180:f3::42",
        "2604:a880:1:20::51:f001", "2606:4700::6810:f8f9", "2606:4700::6810:f9f9", "2606:4700::6812:1a80",
        "2606:4700::6812:1b80", "2606:4700::6812:237", "2606:4700::6812:337", "2606:4700:3033::6812:2ccc",
        "2606:4700:3033::6812:2dcc", "2606:4700:3033::6818:7b35", "2606:4700:3034::681c:16a",
        "2606:4700:3035::6818:7a35", "2606:4700:3035::681f:5a8a", "2606:4700:3036::681c:6a",
        "2606:4700:3036::681f:5b8a", "2606:4700:60:0:a71e:6467:cef8:2a56", "2620:10a:80bb::10",
        "2620:10a:80bb::20", "2620:10a:80bb::30" "2620:10a:80bc::10", "2620:10a:80bc::20",
        "2620:10a:80bc::30", "2620:119:fc::2", "2620:119:fc::3", "2620:fe::10", "2620:fe::11",
        "2620:fe::9", "2620:fe::fe:10", "2620:fe::fe:11", "2620:fe::fe:9", "2620:fe::fe",
        "2a00:5a60::ad1:ff", "2a00:5a60::ad2:ff", "2a00:5a60::bad1:ff", "2a00:5a60::bad2:ff",
        "2a00:d880:5:bf0::7c93", "2a01:4f8:1c0c:8233::1", "2a01:4f8:1c1c:6b4b::1", "2a01:4f8:c2c:52bf::1",
        "2a01:4f9:c010:43ce::1", "2a01:4f9:c01f:4::abcd", "2a01:7c8:d002:1ef:5054:ff:fe40:3703",
        "2a01:9e00::54", "2a01:9e00::55", "2a01:9e01::54", "2a01:9e01::55",
        "2a02:1205:34d5:5070:b26e:bfff:fe1d:e19b", "2a03:4000:38:53c::2",
        "2a03:b0c0:0:1010::e9a:3001", "2a04:bdc7:100:70::abcd", "2a05:fc84::42", "2a05:fc84::43",
        "2a07:a8c0::", "2a0d:4d00:81::1", "2a0d:5600:33:3::abcd", "35.198.2.76", "35.231.247.227",
        "45.32.55.94", "45.67.219.208", "45.76.113.31", "45.77.180.10", "45.90.28.0",
        "46.101.66.244", "46.227.200.54", "46.227.200.55", "46.239.223.80", "8.8.4.4",
        "8.8.8.8", "83.77.85.7", "88.198.91.187", "9.9.9.10", "9.9.9.11", "9.9.9.9",
        "94.130.106.88", "95.216.181.228", "95.216.212.177", "96.113.151.148",
    ]
}

# additional hostnames to block
additional_doh_names: List[str] = [
    'dns.google.com'
]

# additional IPs to block
additional_doh_ips: List[str] = [

]

doh_hostnames, doh_ips = default_blocklist['hostnames'], default_blocklist['ips']

# convert to sets for faster lookups
doh_hostnames = set(doh_hostnames)
doh_ips = set(doh_ips)


def _has_dns_message_content_type(flow):
    """
    Check if HTTP request has a DNS-looking 'Content-Type' header

    :param flow: mitmproxy flow
    :return: True if 'Content-Type' header is DNS-looking, False otherwise
    """
    doh_content_types = ['application/dns-message']
    if 'Content-Type' in flow.request.headers:
        if flow.request.headers['Content-Type'] in doh_content_types:
            return True
    return False


def _request_has_dns_query_string(flow):
    """
    Check if the query string of a request contains the parameter 'dns'

    :param flow: mitmproxy flow
    :return: True is 'dns' is a parameter in the query string, False otherwise
    """
    return 'dns' in flow.request.query


def _request_is_dns_json(flow):
    """
    Check if the request looks like DoH with JSON.

    The only known implementations of DoH with JSON are Cloudflare and Google.

    For more info, see:
    - https://developers.cloudflare.com/1.1.1.1/dns-over-https/json-format/
    - https://developers.google.com/speed/public-dns/docs/doh/json

    :param flow: mitmproxy flow
    :return: True is request looks like DNS JSON, False otherwise
    """
    # Header 'Accept: application/dns-json' is required in Cloudflare's DoH JSON API
    # or they return a 400 HTTP response code
    if 'Accept' in flow.request.headers:
        if flow.request.headers['Accept'] == 'application/dns-json':
            return True
    # Google's DoH JSON API is https://dns.google/resolve
    path = flow.request.path.split('?')[0]
    if flow.request.host == 'dns.google' and path == '/resolve':
        return True
    return False


def _request_has_doh_looking_path(flow):
    """
    Check if the path looks like it's DoH.
    Most common one is '/dns-query', likely because that's what's in the RFC

    :param flow: mitmproxy flow
    :return: True if path looks like it's DoH, otherwise False
    """
    doh_paths = [
        '/dns-query',       # used in example in RFC 8484 (see https://tools.ietf.org/html/rfc8484#section-4.1.1)
    ]
    path = flow.request.path.split('?')[0]
    return path in doh_paths


def _requested_hostname_is_in_doh_blocklist(flow):
    """
    Check if server hostname is in our DoH provider blocklist.

    The current blocklist is taken from https://github.com/curl/curl/wiki/DNS-over-HTTPS.

    :param flow: mitmproxy flow
    :return: True if server's hostname is in DoH blocklist, otherwise False
    """
    hostname = flow.request.host
    ip = flow.server_conn.address
    return hostname in doh_hostnames or hostname in doh_ips or ip in doh_ips


doh_request_detection_checks = [
    _has_dns_message_content_type,
    _request_has_dns_query_string,
    _request_is_dns_json,
    _requested_hostname_is_in_doh_blocklist,
    _request_has_doh_looking_path
]


def request(flow):
    for check in doh_request_detection_checks:
        is_doh = check(flow)
        if is_doh:
            ctx.log.warn("[DoH Detection] DNS over HTTPS request detected via method \"%s\"" % check.__name__)
            flow.kill()
            break
