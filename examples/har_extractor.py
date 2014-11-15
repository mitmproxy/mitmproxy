"""
    This inline script utilizes harparser.HAR from https://github.com/JustusW/harparser
    to generate a HAR log object.
"""
from harparser import HAR
from datetime import datetime, timedelta, tzinfo


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "Z"


class _HARLog(HAR.log):
    def __init__(self):
        HAR.log.__init__(self, {"version": "1.2",
                                "creator": {"name": "MITMPROXY HARExtractor",
                                            "version": "0.1",
                                            "comment": ""},
                                "pages": [],
                                "entries": []})

    def reset(self):
        self.__init__()

    def add(self, obj):
        if isinstance(obj, HAR.pages):
            self['pages'].append(obj)
        if isinstance(obj, HAR.entries):
            self['entries'].append(obj)


def start(context, argv):
    HARLog.reset()


def clientconnect(context, conn_handler):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    import time
    context.log("clientconnect" + str(time.time()))


def serverconnect(context, conn_handler):
    """
        Called when the proxy initiates a connection to the target server. Note that a
        connection can correspond to multiple HTTP requests
    """
    CONNECT_TIMES.pop(conn_handler.server_conn.address.address, None)
    SSL_TIMES.pop(conn_handler.server_conn.address.address, None)
    import time
    context.log("serverconnect " + str(time.time()))


def request(context, flow):
    """
        Called when a client request has been received.
    """
    # print_attributes(flow)
    # print_attributes(context)
    import time
    context.log("request " + str(time.time()) + " " + str(flow.request.timestamp_start))


def responseheaders(context, flow):
    """
        Called when the response headers for a server response have been received,
        but the response body has not been processed yet. Can be used to tell mitmproxy
        to stream the response.
    """
    context.log("responseheaders")


def response(context, flow):
    """
       Called when a server response has been received.
    """
    import time
    context.log("response " + str(time.time()) + " " + str(flow.request.timestamp_start))
    context.log("response " + str(time.time()) + " " + str(flow.response.timestamp_end))
    connect_time = CONNECT_TIMES.get(flow.server_conn.address.address,
                                     int((flow.server_conn.timestamp_tcp_setup
                                          - flow.server_conn.timestamp_start)
                                         * 1000))
    CONNECT_TIMES[flow.server_conn.address.address] = -1

    ssl_time = -1
    if flow.server_conn.timestamp_ssl_setup is not None:
        ssl_time = SSL_TIMES.get(flow.server_conn.address.address,
                                 int((flow.server_conn.timestamp_ssl_setup
                                      - flow.server_conn.timestamp_tcp_setup)
                                     * 1000))
        SSL_TIMES[flow.server_conn.address.address] = -1

    timings = {'send': int((flow.request.timestamp_end - flow.request.timestamp_start) * 1000),
               'wait': int((flow.response.timestamp_start - flow.request.timestamp_end) * 1000),
               'receive': int((flow.response.timestamp_end - flow.response.timestamp_start) * 1000),
               'connect': connect_time,
               'ssl': ssl_time}

    full_time = 0
    for item in timings.values():
        if item > -1:
            full_time += item

    entry = HAR.entries({"startedDateTime": datetime.fromtimestamp(flow.request.timestamp_start, tz=UTC()).isoformat(),
                         "time": full_time,
                         "request": {"method": flow.request.method,
                                     "url": flow.request.url,
                                     "httpVersion": ".".join([str(v) for v in flow.request.httpversion]),
                                     "cookies": [{"name": k.strip(), "value": v[0]}
                                                 for k, v in (flow.request.get_cookies() or {}).iteritems()],
                                     "headers": [{"name": k, "value": v}
                                                 for k, v in flow.request.headers],
                                     "queryString": [{"name": k, "value": v}
                                                     for k, v in flow.request.get_query()],
                                     "headersSize": len(str(flow.request.headers).split("\r\n\r\n")[0]),
                                     "bodySize": len(flow.request.content), },
                         "response": {"status": flow.response.code,
                                      "statusText": flow.response.msg,
                                      "httpVersion": ".".join([str(v) for v in flow.response.httpversion]),
                                      "cookies": [{"name": k.strip(), "value": v[0]}
                                                  for k, v in (flow.response.get_cookies() or {}).iteritems()],
                                      "headers": [{"name": k, "value": v}
                                                  for k, v in flow.response.headers],
                                      "content": {"size": len(flow.response.content),
                                                  "compression": len(flow.response.get_decoded_content()) - len(
                                                      flow.response.content),
                                                  "mimeType": flow.response.headers.get('Content-Type', ('', ))[0]},
                                      "redirectURL": flow.response.headers.get('Location', ''),
                                      "headersSize": len(str(flow.response.headers).split("\r\n\r\n")[0]),
                                      "bodySize": len(flow.response.content), },
                         "cache": {},
                         "timings": timings, })

    if flow.request.url in HARPAGE_LIST or flow.request.headers.get('Referer', None) is None:
        PAGE_COUNT[1] += 1
        page_id = "_".join([str(v) for v in PAGE_COUNT])
        HARLog.add(HAR.pages({"startedDateTime": entry['startedDateTime'],
                              "id": page_id,
                              "title": flow.request.url, }))
        PAGE_REF[flow.request.url] = page_id
        entry['pageref'] = page_id

    if flow.request.headers.get('Referer', (None, ))[0] in PAGE_REF.keys():
        entry['pageref'] = PAGE_REF[flow.request.headers['Referer'][0]]
        PAGE_REF[flow.request.url] = entry['pageref']

    HARLog.add(entry)


def error(context, flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code.
    """
    # context.log("error")


def clientdisconnect(context, conn_handler):
    """
        Called when a client disconnects from the proxy.
    """
    # print "clientdisconnect"
    # print_attributes(context._master)
    # print_attributes(conn_handler)


def done(context):
    """
        Called once on script shutdown, after any other events.
    """
    from pprint import pprint
    import json

    pprint(json.loads(HARLog.json()))
    print HARLog.json()
    print HARLog.compress()
    print "%s%%" % str(100. * len(HARLog.compress()) / len(HARLog.json()))


def print_attributes(obj, filter=None):
    for attr in dir(obj):
        # if "__" in attr:
        # continue
        if filter is not None and filter not in attr:
            continue
        value = getattr(obj, attr)
        print "%s.%s" % ('obj', attr), value, type(value)


HARPAGE_LIST = ['https://github.com/']
HARLog = _HARLog()

CONNECT_TIMES = {}
SSL_TIMES = {}
PAGE_REF = {}
PAGE_COUNT = ['autopage', 0]
