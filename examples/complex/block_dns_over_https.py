"""
This module is for blocking DNS over HTTPS requests.

It loads a blocklist of IPs and hostnames that are known to serve DNS over HTTPS requests.
It also uses headers, query params, and paths to detect DoH (and block it)
"""
import json
import re
import os
import urllib.request
from typing import List

import dns.query
import dns.rdatatype
import dns.message
import dns.resolver
import dns.rdtypes.IN.A
import dns.rdtypes.IN.AAAA

from mitmproxy import ctx

# filename we'll save the blocklist to so we don't have to re-generate it every time
blocklist_filename = 'blocklist.json'

# additional hostnames to block
additional_doh_names: List[str] = [
    'dns.google.com'
]

# additional IPs to block
additional_doh_ips: List[str] = [

]


def get_doh_providers():
    """
    Scrape a list of DoH providers from curl's wiki page.
    :return: a generator of dicts containing information about the DoH providers
    """
    https_url_re = re.compile(r'https://'
                              r'(?P<hostname>[0-9a-zA-Z._~-]+)'
                              r'(?P<port>:[0-9]+)?'
                              r'(?P<path>[0-9a-zA-Z._~/-]+)?')

    provider_re = re.compile(r'(\[([^\]]+)\]\(([^)]+))\)|(.*)')
    # URLs that are not DoH URLs
    do_not_include = ['my.nextdns.io', 'blog.cloudflare.com']
    found_table = False
    with urllib.request.urlopen('https://raw.githubusercontent.com/wiki/curl/curl/DNS-over-HTTPS.md') as fp:
        for line in fp:
            line = line.decode()
            if line.startswith('|'):
                if not found_table:
                    found_table = True
                    continue
                cols = line.split('|')
                provider_col = cols[1].strip()
                website = None
                provider_name = None
                matches = provider_re.findall(provider_col)
                if matches[0][3] != '':
                    provider_name = matches[0][3]
                if matches[0][1] != '':
                    provider_name = matches[0][1]
                if matches[0][2] != '':
                    website = matches[0][2]
                if provider_name is not None:
                    provider_name = re.sub(r'([^[]+)\s?(.*)', r'\1', provider_name)
                    while provider_name[-1] == ' ':
                        provider_name = provider_name[:-1]
                url_col = cols[2]
                doh_url_matches = https_url_re.findall(url_col)
                if len(doh_url_matches) == 0:
                    continue
                else:
                    for doh_url in doh_url_matches:
                        if doh_url[0] in do_not_include:
                            continue
                        yield {
                            'name': provider_name,
                            'website': website,
                            'url': 'https://{}{}{}'.format(doh_url[0],
                                                           ':{}'.format(doh_url[1])
                                                           if len(doh_url[1]) != 0
                                                           else '', doh_url[2]),
                            'hostname': doh_url[0],
                            'port': doh_url[1] if len(doh_url[1]) != 0 else '443',
                            'path': doh_url[2],
                        }
            if found_table and line.startswith('#'):
                break
    return


def get_ips(hostname):
    """
    Lookup all A and AAAA records for given hostname
    :param hostname: the name to lookup
    :return: a list of IP addresses returned
    """
    default_nameserver = dns.resolver.Resolver().nameservers[0]
    ips = list()
    rdtypes = [dns.rdatatype.A, dns.rdatatype.AAAA]
    for rdtype in rdtypes:
        q = dns.message.make_query(hostname, rdtype)
        r = dns.query.udp(q, default_nameserver)
        if r.flags & dns.flags.TC:
            r = dns.query.tcp(q, default_nameserver)
        for a in r.answer:
            for i in a.items:
                if isinstance(i, dns.rdtypes.IN.A.A) or isinstance(i, dns.rdtypes.IN.AAAA.AAAA):
                    ips.append(str(i.address))
    return ips


def load_blocklist():
    """
    Load a tuple containing two lists, in the form of (hostnames, ips).
    It will attempt to load it from a file, and if that file is not found,
    it will generate the blocklist and save it to a file.

    :return: a ``tuple`` of (``list``, ``list``), the hostnames and IPs to block
    """
    if os.path.isfile(blocklist_filename):
        with open(blocklist_filename, 'r') as fp:
            j = json.load(fp)
        doh_hostnames, doh_ips = j['hostnames'], j['ips']
    else:
        doh_hostnames = list([i['hostname'] for i in get_doh_providers()])
        doh_ips = list()
        for hostname in doh_hostnames:
            ips = get_ips(hostname)
            doh_ips.extend(ips)
    doh_hostnames.extend(additional_doh_names)
    doh_ips.extend(additional_doh_ips)
    with open(blocklist_filename, 'w') as fp:
        obj = {
            'hostnames': doh_hostnames,
            'ips': doh_ips
        }
        json.dump(obj, fp=fp)
    return doh_hostnames, doh_ips


# load DoH hostnames and IP addresses to block
doh_hostnames, doh_ips = load_blocklist()
ctx.log.info('DoH blocklist loaded')

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


def _requested_hostname_is_in_doh_blacklist(flow):
    """
    Check if server hostname is in our DoH provider blacklist.

    The current blacklist is taken from https://github.com/curl/curl/wiki/DNS-over-HTTPS.

    :param flow: mitmproxy flow
    :return: True if server's hostname is in DoH blacklist, otherwise False
    """
    hostname = flow.request.host
    ip = flow.server_conn.address
    return hostname in doh_hostnames or hostname in doh_ips or ip in doh_ips


doh_request_detection_checks = [
    _has_dns_message_content_type,
    _request_has_dns_query_string,
    _request_is_dns_json,
    _requested_hostname_is_in_doh_blacklist,
    _request_has_doh_looking_path
]


def request(flow):
    for check in doh_request_detection_checks:
        is_doh = check(flow)
        if is_doh:
            ctx.log.warn("[DoH Detection] DNS over HTTPS request detected via method \"%s\"" % check.__name__)
            flow.kill()
            break
