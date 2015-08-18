from libmproxy.protocol.http import decoded
from libmproxy import version
import jsbeautifier
import sys
import bs4
import platform

def start(context, argv):
    if len(argv) != 1:
        raise ValueError('Usage: -s "beautify_javascript"')

def response(context, flow):
    try:
        header = '// beautified by jsbeautifier ' + jsbeautifier.__version__ + ' via mitmproxy ' + version.VERSION
        server_header = '// running on Python ' + sys.version.replace('\n', '') + ' ' + (' '.join(platform.uname()))

        content_type = flow.response.headers.get_first('Content-Type', '').lower()
        # this sucks; should use more better logic....
        if content_type == 'application/javascript;charset=UTF-8' or content_type == 'text/javascript;charset=utf-8' or content_type == 'text/application' or content_type == 'application/x-javascript' or content_type == 'text/javascript' or content_type == 'application/javascript' or content_type == 'text/javascript; charset=utf-8' or content_type == 'application/x-javascript; charset=utf-8' or content_type == 'text/javascript; charser=utf-8':
            with decoded(flow.response):
                beautified_content = jsbeautifier.beautify(flow.response.content)
                flow.response.content = header + '\n' + server_header + '\n' + beautified_content
        if content_type == 'text/html; charset=utf-8':
            with decoded(flow.response):
                header += ' using Beautiful Soup ' + bs4.__version__
                html = bs4.BeautifulSoup(unicode(flow.response.content, "utf-8"), 'html.parser')
                for script in html.find_all('script'):
                    if script.string:
                        script.string = '\n' + header + '\n' + server_header + '\n' + jsbeautifier.beautify(script.string) + '\n'

                flow.response.content = str(html)
    except:
      context.log(sys.exc_info()[0])
      raise
