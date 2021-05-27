from datetime import datetime
from datetime import timezone


class HarBuilder():
    # Default templates for building har chunks as dictionaries

    @staticmethod
    def har():
        return {
            "log": HarBuilder.log()
        }

    @staticmethod
    def log():
        return {
            "version": "1.1",
            "creator": {
                "name": "BrowserUp Proxy",
                "version": "0.1",
                "comment": ""
            },
            "entries": [],
            "pages": []
        }

    @staticmethod
    def page_timings():
        return {
            "onContentLoad": 0,
            "onLoad": 0,
            "comment": ""
        }

    @staticmethod
    def page(title="", id="", started_date_time=str(datetime.now(tz=timezone.utc).isoformat())):
        return {
            "title": title,
            "id": id,
            "startedDateTime": started_date_time,
            "pageTimings": HarBuilder.page_timings()
        }

    @staticmethod
    def post_data():
        return {
            "mimeType": "multipart/form-data",
            "params": [],
            "text": "plain posted data",
            "comment": ""
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
            "additional": {}
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
            "receive": 0
        }

    @staticmethod
    def entry_response():
        return {
            "status": 0,
            "statusText": "",
            "httpVersion": "",
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
            "comment": 0,
        }

    @staticmethod
    def entry_response_for_failure():
        result = HarBuilder.entry_response()
        result['status'] = 0
        result['statusText'] = ""
        result['httpVersion'] = "unknown"
        result['_errorMessage'] = "No response received"
        return result

    @staticmethod
    def entry():
        return {
            "pageref": "",
            "startedDateTime": "",
            "time": 0,
            "request": {},
            "response": {},
            "_webSocketMessages": [],
            "cache": {},
            "timings": HarBuilder.entry_timings(),
            "serverIPAddress": "",
            "connection": "",
            "comment": ""
        }
