import json
from textwrap import dedent

import netlib.tutils
from netlib.http import Headers
from mitmproxy import flow_export
from . import tutils

req_get = netlib.tutils.treq(
    method='GET',
    content='',
)

req_post = netlib.tutils.treq(
    method='POST',
    headers=None,
)

req_patch = netlib.tutils.treq(
    method='PATCH',
    path=b"/path?query=param",
)


class TestExportCurlCommand():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = """curl -H 'header:qvalue' -H 'content-length:7' 'http://address/path'"""
        assert flow_export.curl_command(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = """curl -X POST 'http://address/path' --data-binary 'content'"""
        assert flow_export.curl_command(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = """curl -H 'header:qvalue' -H 'content-length:7' -X PATCH 'http://address/path?query=param' --data-binary 'content'"""
        assert flow_export.curl_command(flow) == result


class TestExportPythonCode():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = dedent("""
            import requests

            url = 'http://address/path'

            headers = {
                'header': 'qvalue',
                'content-length': '7',
            }

            response = requests.request(
                method='GET',
                url=url,
                headers=headers,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = dedent("""
            import requests

            url = 'http://address/path'

            data = '''content'''

            response = requests.request(
                method='POST',
                url=url,
                data=data,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result

    def test_post_json(self):
        req_post.content = '{"name": "example", "email": "example@example.com"}'
        req_post.headers = Headers(content_type="application/json")
        flow = tutils.tflow(req=req_post)
        result = dedent("""
            import requests

            url = 'http://address/path'

            headers = {
                'content-type': 'application/json',
            }

            json = {
                "name": "example",
                "email": "example@example.com"
            }

            response = requests.request(
                method='POST',
                url=url,
                headers=headers,
                json=json,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = dedent("""
            import requests

            url = 'http://address/path'

            headers = {
                'header': 'qvalue',
                'content-length': '7',
            }

            params = {
                'query': 'param',
            }

            data = '''content'''

            response = requests.request(
                method='PATCH',
                url=url,
                headers=headers,
                params=params,
                data=data,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result


class TestRawRequest():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = dedent("""
            GET /path HTTP/1.1\r
            header: qvalue\r
            content-length: 7\r
            host: address:22\r
            \r
        """).strip(" ").lstrip()
        assert flow_export.raw_request(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = dedent("""
            POST /path HTTP/1.1\r
            content-type: application/json\r
            host: address:22\r
            \r
            {"name": "example", "email": "example@example.com"}
        """).strip()
        assert flow_export.raw_request(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = dedent("""
            PATCH /path?query=param HTTP/1.1\r
            header: qvalue\r
            content-length: 7\r
            host: address:22\r
            \r
            content
        """).strip()
        assert flow_export.raw_request(flow) == result

class TestExportLocustCode():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = """
from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.path()

    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
        )

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000
        """.strip()

        assert flow_export.locust_code(flow) == result

    def test_post(self):
        req_post.content = '''content'''
        req_post.headers = ''
        flow = tutils.tflow(req=req_post)
        result = """
from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.path()

    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        data = '''content'''

        self.response = self.client.request(
            method='POST',
            url=url,
            data=data,
        )

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000

        """.strip()

        assert flow_export.locust_code(flow) == result


    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = """
from locust import HttpLocust, TaskSet, task

class UserBehavior(TaskSet):
    def on_start(self):
        ''' on_start is called when a Locust start before any task is scheduled '''
        self.path()

    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        params = {
            'query': 'param',
        }

        data = '''content'''

        self.response = self.client.request(
            method='PATCH',
            url=url,
            headers=headers,
            params=params,
            data=data,
        )

    ### Additional tasks can go here ###


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 3000

        """.strip()

        assert flow_export.locust_code(flow) == result


class TestExportLocustTask():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = '    ' + """
    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        self.response = self.client.request(
            method='GET',
            url=url,
            headers=headers,
        )
        """.strip() + '\n'

        assert flow_export.locust_task(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = '    ' + """
    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        data = '''content'''

        self.response = self.client.request(
            method='POST',
            url=url,
            data=data,
        )
        """.strip() + '\n'

        assert flow_export.locust_task(flow) == result


    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = '    ' + """
    @task()
    def path(self):
        url = self.locust.host + '/path'
        
        headers = {
            'header': 'qvalue',
            'content-length': '7',
        }

        params = {
            'query': 'param',
        }

        data = '''content'''

        self.response = self.client.request(
            method='PATCH',
            url=url,
            headers=headers,
            params=params,
            data=data,
        )
        """.strip() + '\n'

        assert flow_export.locust_task(flow) == result


class TestIsJson():

    def test_empty(self):
        assert flow_export.is_json(None, None) == False

    def test_json_type(self):
        headers = Headers(content_type="application/json")
        assert flow_export.is_json(headers, "foobar") == False

    def test_valid(self):
        headers = Headers(content_type="application/foobar")
        j = flow_export.is_json(headers, '{"name": "example", "email": "example@example.com"}')
        assert j == False

    def test_valid(self):
        headers = Headers(content_type="application/json")
        j = flow_export.is_json(headers, '{"name": "example", "email": "example@example.com"}')
        assert isinstance(j, dict)
