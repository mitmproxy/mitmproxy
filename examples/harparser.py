"""
    This module implements HAR as per specification version 1.2.
"""
from collections import MutableMapping
from json import dumps, loads
from zlib import compress, decompress


class HAREncodable(MutableMapping):
    """
        Base class that allows for recursive HAR structures using HAR as map.
    """
    __required__ = {}
    __optional__ = {}

    def __init__(self, *args, **kwargs):
        """
            Initialize the private dict that is used to actually store the information.
            Fills it with the content given in args/kwargs then checks against
            __required__ for missing mandatory fields.

            Important: If no parameters are given no checks will be done for convenience.
        """
        self.__dict__ = {}

        if len(args) > 0:
            kwargs = args[0]
        elif len(kwargs) == 0:
            return

        for key, value in kwargs.items():
            self[key] = value

        for key in self.__required__:
            self[key]

    def __setitem__(self, key, value):
        """
            Exposes self.__dict__.__setitem__ with typecasting.

            Typecast any item to the correct type based on key name and position as
            implicitly provided by __required__ and __optional__. If a key is used
            that is not in the specification it will be added without type casting!
        """
        item_type = self.__required__.get(key, self.__optional__.get(key, None))
        if type(item_type) is type:
            value = item_type(value)
        elif type(item_type) is list:
            value = [HAR[key](v) for v in value]
        elif type(item_type) is dict:
            value = HAR[key](value)
        # If it is None or not in the handled cases we would use pass anyway.

        return self.__dict__.__setitem__(key, value)

    def __getitem__(self, *args, **kwargs):
        """
            Directly exposes self.__dict__.__getitem__
        """
        return self.__dict__.__getitem__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        """
            Directly exposes self.__dict__.__delitem__
        """
        return self.__dict__.__delitem__(*args, **kwargs)

    def __len__(self):
        """
            Directly exposes self.__dict__.__len__
        """
        return self.__dict__.__len__()

    def __iter__(self):
        """
            Directly exposes self.__dict__.__iter__
        """
        return self.__dict__.__iter__()

    def json(self, json_string=None):
        """
            Convenience method allowing easy dumping to and loading from json.
        """
        if json_string is not None:
            return self.__init__(loads(json_string))
        dump = self
        if isinstance(self, HAR.log):
            dump = {"log": dump}
        return dumps(dump, default=lambda x: dict(x))

    def compress(self):
        """
            Convenience method for compressing the json output.
        """
        return compress(self.json())

    def decompress(self, compressed_json_string):
        """
            Convenience method for decompressing json input.
        """
        return self.json(json_string=decompress(compressed_json_string))


class _HAR(MutableMapping, object):
    """
        HAR implementation as per specification version 1.2 ()
        This class maps the specification contained in __map__ to dynamic subclasses stored in __classes__.
        It then exposes all of this by implementing MutableMapping, the generated subclasses being its keys.
    """
    __map__ = {"log": {"__required__": {"version": str,
                                        "creator": {},
                                        "entries": [], },
                       "__optional__": {"browser": {},
                                        "pages": [],
                                        "comment": str, }},
               "creator": {"__required__": {"name": str,
                                            "version": str, },
                           "__optional__": {"comment": str}, },
               "browser": {"__required__": {"name": str,
                                            "version": str, },
                           "__optional__": {"comment": str}, },
               "pages": {"__required__": {"startedDateTime": str,
                                          "id": str,
                                          "title": str, },
                         "__optional__": {"pageTimings": {},
                                          "comment": str}, },
               "pageTimings": {"__required__": {},
                               "__optional__": {"onContentLoad": int,
                                                "onLoad": int,
                                                "comment": str}, },
               "entries": {"__required__": {"startedDateTime": str,
                                            "time": int,
                                            "request": {},
                                            "response": {},
                                            "cache": {},
                                            "timings": {}, },
                           "__optional__": {"pageref": str,
                                            "serverIPAddress": str,
                                            "connection": str,
                                            "comment": str}, },
               "request": {"__required__": {"method": str,
                                            "url": str,
                                            "httpVersion": str,
                                            "cookies": [],
                                            "headers": [],
                                            "queryString": [],
                                            "headersSize": int,
                                            "bodySize": int, },
                           "__optional__": {"postData": {},
                                            "comment": str}, },
               "response": {"__required__": {"status": int,
                                             "statusText": str,
                                             "httpVersion": str,
                                             "cookies": [],
                                             "headers": [],
                                             "content": {},
                                             "redirectURL": str,
                                             "headersSize": int,
                                             "bodySize": int, },
                            "__optional__": {"comment": str}, },
               "cookies": {"__required__": {"name": str,
                                            "value": str, },
                           "__optional__": {"path": str,
                                            "domain": str,
                                            "expires": str,
                                            "httpOnly": bool,
                                            "secure": bool,
                                            "comment": str}, },
               "headers": {"__required__": {"name": str,
                                            "value": str, },
                           "__optional__": {"comment": str}, },
               "queryString": {"__required__": {"name": str,
                                                "value": str, },
                               "__optional__": {"comment": str}, },
               "postData": {"__required__": {"mimeType": str,
		       			     "text": str,},
                            "__optional__": {"comment": str,
				             "params": [],}, },
               "params": {"__required__": {"name": str, },
                          "__optional__": {"value": str,
                                           "fileName": str,
                                           "contentType": str,
                                           "comment": str}, },
               "content": {"__required__": {"size": int,
                                            "mimeType": str, },
                           "__optional__": {"compression": int,
                                            "text": str,
                                            "comment": str}, },
               "cache": {"__required__": {},
                         "__optional__": {"beforeRequest": {},
                                          "afterRequest": {},
                                          "comment": str}, },
               "beforeRequest": {"__required__": {"lastAccess": str,
                                                  "eTag": str,
                                                  "hitCount": int, },
                                 "__optional__": {"expires": str,
                                                  "comment": str, }, },
               "afterRequest": {"__required__": {"lastAccess": str,
                                                 "eTag": str,
                                                 "hitCount": int, },
                                "__optional__": {"expires": str,
                                                 "comment": str, }, },
               "timings": {"__required__": {"send": int,
                                            "wait": int,
                                            "receive": int, },
                           "__optional__": {"blocked": int,
                                            "dns": int,
                                            "connect": int,
                                            "ssl": int,
                                            "comment": str, }, }}

    def __init__(self):
        """
            Exposes the classes mapped from __map__ extending HAREncodable as a
            MutableMapping, dict like object.
        """
        self.__classes__ = dict([(name,
                                  type(name, (HAREncodable, ), self.__map__[name]))
                                 for name in self.__map__])

    def __getattr__(self, item):
        """
            Exposes __getitem__ keys as attributes.
        """
        return self[item]

    def __getitem__(self, *args, **kwargs):
        """
            Directly exposes self.__classes__.__getitem__
        """
        return self.__classes__.__getitem__(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        """
            Directly exposes self.__classes__.__setitem__
        """
        return self.__classes__.__setitem__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        """
            Directly exposes self.__classes__.__delitem__
        """
        return self.__classes__.__delitem__(*args, **kwargs)

    def __iter__(self):
        """
            Directly exposes self.__classes__.__iter__
        """
        return self.__classes__.__iter__()

    def __len__(self):
        """
            Directly exposes self.__classes__.__len__
        """
        return self.__classes__.__len__()


# Make an instance of _HAR available as HAR. If required one can
# instantiate another object from _HAR to avoid interference with
# other peoples code.
HAR = _HAR()
