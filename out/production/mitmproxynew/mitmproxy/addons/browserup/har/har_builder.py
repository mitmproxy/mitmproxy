from datetime import datetime
from datetime import timezone

class HarBuilder:

    def har(self):
        return {
            "log": self.log()
        }

    def log(self):
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

    def page_timings(self):
        return {
            "onContentLoad": 0,
            "onLoad": 0,
            "comment": ""
        }

    def page(self, title="", id="", started_date_time=datetime.utcnow().isoformat()):
        return {
            "title": title,
            "id": id,
            "startedDateTime": started_date_time,
            "pageTimings": self.page_timings()
        }

    def post_data(self):
        return {
            "mimeType": "multipart/form-data",
            "params": [],
            "text": "plain posted data",
            "comment": ""
        }

    def entry_request(self):
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

    def timings(self):
        return {
            "blockedNanos": -1,
            "dnsNanos": -1,
            "connectNanos": -1,
            "sslNanos": -1,
            "sendNanos": 0,
            "waitNanos": 0,
            "receiveNanos": 0,
            "comment": ""
        }

    def http_connect_timing(self):
        return {
            "blockedTimeNanos": -1,
            "dnsTimeNanos": -1,
            "connectTimeNanos": -1,
            "sslHandshakeTimeNanos": -1,
        }


    def entry_response(self):
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

    def entry_response_for_failure(self):
        result = self.entry_response()
        result['status'] = 0
        result['statusText'] = ""
        result['httpVersion'] = "unknown"
        result['_errorMessage'] = "No response received"
        return result

    def entry(self):
        return {
            "pageref": "",
            "startedDateTime": "",
            "time": 0,
            "request": {},
            "response": {},
            "cache": {},
            "timings": self.timings(),
            "serverIPAddress": "",
            "connection": "",
            "comment": ""
        }
