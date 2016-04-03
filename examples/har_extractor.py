"""
    This inline script utilizes harparser.HAR from
    https://github.com/JustusW/harparser to generate a HAR log object.
"""
import six
from harparser import HAR

from datetime import datetime


class _HARLog(HAR.log):
    # The attributes need to be registered here for them to actually be
    # available later via self. This is due to HAREncodable linking __getattr__
    # to __getitem__. Anything that is set only in __init__ will just be added
    # as key/value pair to self.__classes__.
    __page_list__ = []
    __page_count__ = 0
    __page_ref__ = {}

    def __init__(self, page_list=[]):
        self.__page_list__ = page_list
        self.__page_count__ = 0
        self.__page_ref__ = {}

        HAR.log.__init__(self, {"version": "1.2",
                                "creator": {"name": "MITMPROXY HARExtractor",
                                            "version": "0.1",
                                            "comment": ""},
                                "pages": [],
                                "entries": []})

    def reset(self):
        self.__init__(self.__page_list__)

    def add(self, obj):
        if isinstance(obj, HAR.pages):
            self['pages'].append(obj)
        if isinstance(obj, HAR.entries):
            self['entries'].append(obj)

    def create_page_id(self):
        self.__page_count__ += 1
        return "autopage_%s" % str(self.__page_count__)

    def set_page_ref(self, page, ref):
        self.__page_ref__[page] = ref

    def get_page_ref(self, page):
        return self.__page_ref__.get(page, None)

    def get_page_list(self):
        return self.__page_list__


def start(context, argv):
    """
        On start we create a HARLog instance. You will have to adapt this to
        suit your actual needs of HAR generation. As it will probably be
        necessary to cluster logs by IPs or reset them from time to time.
    """
    context.dump_file = None
    if len(argv) > 1:
        context.dump_file = argv[1]
    else:
        raise ValueError(
            'Usage: -s "har_extractor.py filename" '
            '(- will output to stdout, filenames ending with .zhar '
            'will result in compressed har)'
        )
    context.HARLog = _HARLog()
    context.seen_server = set()


def response(context, flow):
    """
       Called when a server response has been received. At the time of this
       message both a request and a response are present and completely done.
    """
    # Values are converted from float seconds to int milliseconds later.
    ssl_time = -.001
    connect_time = -.001
    if flow.server_conn not in context.seen_server:
        # Calculate the connect_time for this server_conn. Afterwards add it to
        # seen list, in order to avoid the connect_time being present in entries
        # that use an existing connection.
        connect_time = (flow.server_conn.timestamp_tcp_setup -
                        flow.server_conn.timestamp_start)
        context.seen_server.add(flow.server_conn)

        if flow.server_conn.timestamp_ssl_setup is not None:
            # Get the ssl_time for this server_conn as the difference between
            # the start of the successful tcp setup and the successful ssl
            # setup. If no ssl setup has been made it is left as -1 since it
            # doesn't apply to this connection.
            ssl_time = (flow.server_conn.timestamp_ssl_setup -
                        flow.server_conn.timestamp_tcp_setup)

    # Calculate the raw timings from the different timestamps present in the
    # request and response object. For lack of a way to measure it dns timings
    # can not be calculated. The same goes for HAR blocked: MITMProxy will open
    # a server connection as soon as it receives the host and port from the
    # client connection. So the time spent waiting is actually spent waiting
    # between request.timestamp_end and response.timestamp_start thus it
    # correlates to HAR wait instead.
    timings_raw = {
        'send': flow.request.timestamp_end - flow.request.timestamp_start,
        'wait': flow.response.timestamp_start - flow.request.timestamp_end,
        'receive': flow.response.timestamp_end - flow.response.timestamp_start,
        'connect': connect_time,
        'ssl': ssl_time
    }

    # HAR timings are integers in ms, so we have to re-encode the raw timings to
    # that format.
    timings = dict([(k, int(1000 * v)) for k, v in six.iteritems(timings_raw)])

    # The full_time is the sum of all timings.
    # Timings set to -1 will be ignored as per spec.
    full_time = sum(v for v in timings.values() if v > -1)

    started_date_time = datetime.utcfromtimestamp(
        flow.request.timestamp_start).isoformat()

    request_query_string = [{"name": k, "value": v}
                            for k, v in flow.request.query or {}]

    response_body_size = len(flow.response.content)
    response_body_decoded_size = len(flow.response.get_decoded_content())
    response_body_compression = response_body_decoded_size - response_body_size

    entry = HAR.entries({
        "startedDateTime": started_date_time,
        "time": full_time,
        "request": {
            "method": flow.request.method,
            "url": flow.request.url,
            "httpVersion": flow.request.http_version,
            "cookies": format_cookies(flow.request.cookies),
            "headers": format_headers(flow.request.headers),
            "queryString": request_query_string,
            "headersSize": len(str(flow.request.headers)),
            "bodySize": len(flow.request.content),
        },
        "response": {
            "status": flow.response.status_code,
            "statusText": flow.response.reason,
            "httpVersion": flow.response.http_version,
            "cookies": format_cookies(flow.response.cookies),
            "headers": format_headers(flow.response.headers),
            "content": {
                "size": response_body_size,
                "compression": response_body_compression,
                "mimeType": flow.response.headers.get('Content-Type', '')
            },
            "redirectURL": flow.response.headers.get('Location', ''),
            "headersSize": len(str(flow.response.headers)),
            "bodySize": response_body_size,
        },
        "cache": {},
        "timings": timings,
    })

    # If the current url is in the page list of context.HARLog or
    # does not have a referrer, we add it as a new pages object.
    if (flow.request.url in context.HARLog.get_page_list() or
            flow.request.headers.get('Referer') is None):
        page_id = context.HARLog.create_page_id()
        context.HARLog.add(
            HAR.pages({
                "startedDateTime": entry['startedDateTime'],
                "id": page_id,
                "title": flow.request.url,
            })
        )
        context.HARLog.set_page_ref(flow.request.url, page_id)
        entry['pageref'] = page_id

    # Lookup the referer in the page_ref of context.HARLog to point this entries
    # pageref attribute to the right pages object, then set it as a new
    # reference to build a reference tree.
    elif context.HARLog.get_page_ref(flow.request.headers.get('Referer')) is not None:
        entry['pageref'] = context.HARLog.get_page_ref(
            flow.request.headers['Referer']
        )
        context.HARLog.set_page_ref(
            flow.request.headers['Referer'], entry['pageref']
        )

    context.HARLog.add(entry)


def done(context):
    """
        Called once on script shutdown, after any other events.
    """
    import pprint
    import json

    json_dump = context.HARLog.json()
    compressed_json_dump = context.HARLog.compress()

    if context.dump_file == '-':
        context.log(pprint.pformat(json.loads(json_dump)))
    elif context.dump_file.endswith('.zhar'):
        file(context.dump_file, "w").write(compressed_json_dump)
    else:
        file(context.dump_file, "w").write(json_dump)
    context.log(
        "HAR log finished with %s bytes (%s bytes compressed)" % (
            len(json_dump), len(compressed_json_dump)
        )
    )
    context.log(
        "Compression rate is %s%%" % str(
            100. * len(compressed_json_dump) / len(json_dump)
        )
    )


def format_cookies(obj):
    if obj:
        return [{"name": k.strip(), "value": v[0]} for k, v in obj.items()]
    return ""


def format_headers(obj):
    if obj:
        return [{"name": k, "value": v} for k, v in obj.fields]
    return ""


def print_attributes(obj, filter_string=None, hide_privates=False):
    """
        Useful helper method to quickly get all attributes of an object and its
        values.
    """
    for attr in dir(obj):
        if hide_privates and "__" in attr:
            continue
        if filter_string is not None and filter_string not in attr:
            continue
        value = getattr(obj, attr)
        print("%s.%s" % ('obj', attr), value, type(value))
