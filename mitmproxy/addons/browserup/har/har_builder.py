from datetime import datetime
from datetime import timezone

DEFAULT_PAGE_TITLE = "Default"
DEFAULT_PAGE_REF = "page_1"


class HarBuilder:
    @staticmethod
    def har():
        return {"log": HarBuilder.log()}

    @staticmethod
    def log():
        return {
            "version": "1.1",
            "creator": {"name": "BrowserUp Proxy", "version": "0.1", "comment": ""},
            "entries": [],
            "pages": [HarBuilder.page(id=DEFAULT_PAGE_REF)],
        }

    @staticmethod
    def page_timings():
        return {"onContentLoad": -1, "onLoad": -1, "comment": ""}

    @staticmethod
    def page(id=DEFAULT_PAGE_REF, title=DEFAULT_PAGE_TITLE):
        return {
            "title": title,
            "id": id,
            "startedDateTime": str(datetime.now(tz=timezone.utc).isoformat()),
            "pageTimings": HarBuilder.page_timings(),
        }

    @staticmethod
    def post_data():
        return {
            "mimeType": "multipart/form-data",
            "params": [],
            "text": "plain posted data",
            "comment": "",
        }

    @staticmethod
    def entry_request():
        return {
            "method": "",
            "url": "",
            "httpVersion": "",
            "cookies": [],
            "headers": [],
            "queryString": [],
            "headersSize": 0,
            "bodySize": 0,
            "comment": "",
        }

    @staticmethod
    def entry_timings():
        return {
            "blocked": -1,
            "dns": -1,
            "connect": -1,
            "ssl": -1,
            "send": 0,
            "wait": 0,
            "receive": 0,
        }

    @staticmethod
    def entry_response():
        return {
            "status": 0,
            "statusText": "",
            "httpVersion": "unknown",
            "cookies": [],
            "headers": [],
            "content": {
                "size": 0,
                "compression": 0,
                "mimeType": "",
                "text": "",
                "encoding": "",
                "comment": "",
            },
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
            "comment": "",
        }

    @staticmethod
    def entry_response_for_failure():
        result = HarBuilder.entry_response()
        result["status"] = 0
        result["statusText"] = ""
        result["httpVersion"] = "unknown"
        result["_errorMessage"] = "No response received"
        return result

    @staticmethod
    def entry(pageref=DEFAULT_PAGE_REF):
        return {
            "pageref": pageref,
            "startedDateTime": str(datetime.now(tz=timezone.utc).isoformat()),
            "time": 0,
            "request": HarBuilder.entry_request(),
            "response": HarBuilder.entry_response(),
            "_webSocketMessages": [],
            "cache": {},
            "timings": HarBuilder.entry_timings(),
            "serverIPAddress": "",
            "connection": "",
            "comment": "",
        }
