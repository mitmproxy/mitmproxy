import urllib
import netlib.http
from textwrap import dedent

import sys, re
if (sys.version_info > (3, 0)):
    from urllib.parse import urlparse
else:
    import urlparse


def curl_command(flow):
    data = "curl "

    for k, v in flow.request.headers.fields:
        data += "-H '%s:%s' " % (k, v)

    if flow.request.method != "GET":
        data += "-X %s " % flow.request.method

    full_url = flow.request.scheme + "://" + flow.request.host + flow.request.path
    data += "'%s'" % full_url

    if flow.request.content:
        data += " --data-binary '%s'" % flow.request.content

    return data


def python_code(flow):
    code = dedent("""
        import requests

        url = '{url}'
        {headers}{params}{data}
        response = requests.request(
            method='{method}',
            url=url,{args}
        )

        print(response.text)
    """).strip()

    components = map(lambda x: urllib.quote(x, safe=""), flow.request.path_components)
    url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)

    args = ""
    headers = ""
    if flow.request.headers:
        lines = ["    '%s': '%s',\n" % (k, v) for k, v in flow.request.headers.fields]
        headers += "\nheaders = {\n%s}\n" % "".join(lines)
        args += "\n    headers=headers,"

    params = ""
    if flow.request.query:
        lines = ["    '%s': '%s',\n" % (k, v) for k, v in flow.request.query]
        params = "\nparams = {\n%s}\n" % "".join(lines)
        args += "\n    params=params,"

    data = ""
    if flow.request.body:
        data = "\ndata = '''%s'''\n" % flow.request.body
        args += "\n    data=data,"

    code = code.format(
        url=url,
        headers=headers,
        params=params,
        data=data,
        method=flow.request.method,
        args=args,
    )

    return code


def raw_request(flow):
    data = netlib.http.http1.assemble_request(flow.request)
    return data


def locust_code(flow):
    code = dedent("""
        from locust import HttpLocust, TaskSet, task

        class UserBehavior(TaskSet):
            def on_start(self):
                ''' on_start is called when a Locust start before any task is scheduled '''
                self.flow()

            @task()
            def flow(self):
                url = '{url}'
                {headers}{params}{data}
                self.response = self.client.request(
                    method='{method}',
                    url=url,{args}
                )

        class WebsiteUser(HttpLocust):
            task_set = UserBehavior
            min_wait=1000
            max_wait=3000

    """).strip()

    components = map(lambda x: urllib.quote(x, safe=""), flow.request.path_components)
    url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)

    args = ""
    headers = ""
    if flow.request.headers:
        lines = ["            '%s': '%s',\n" % (k, v) for k, v in flow.request.headers.fields if k.lower() not in ["host", "cookie"]]
        headers += "\n        headers = {\n%s        }\n" % "".join(lines)
        args += "\n            headers=headers,"

    params = ""
    if flow.request.query:
        lines = ["            '%s': '%s',\n" % (k, v) for k, v in flow.request.query]
        params = "\n        params = {\n%s        }\n" % "".join(lines)
        args += "\n            params=params,"

    data = ""
    if flow.request.body:
        data = "\n        data = '''%s'''\n" % flow.request.body
        args += "\n            data=data,"

    code = code.format(
        url=url,
        headers=headers,
        params=params,
        data=data,
        method=flow.request.method,
        args=args,
    )

    host = flow.request.scheme + "://" + flow.request.host
    code = code.replace(host, "' + self.locust.host +'")
    code = code.replace(urllib.quote_plus(host), "' + urllib.quote_plus(self.locust.host) +'")
    code = code.replace(urllib.quote(host), "' + urllib.quote(self.locust.host) +'")

    return code


def locust_task(flow):
    code = dedent("""
    @task()
    def {name}(self):
        url = '{url}'
        {headers}{params}{data}
        self.response = self.client.request(
            method='{method}',
            url=url,{args}
        )
    """).strip()

    components = map(lambda x: urllib.quote(x, safe=""), flow.request.path_components)
    file_name = "_".join(components)
    name = re.sub('\W|^(?=\d)','_', file_name)
    url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)

    args = ""
    headers = ""
    if flow.request.headers:
        lines = ["        '%s': '%s',\n" % (k, v) for k, v in flow.request.headers.fields if k.lower() not in ["host", "cookie"]]
        headers += "\n    headers = {\n%s    }\n" % "".join(lines)
        args += "\n        headers=headers,"

    params = ""
    if flow.request.query:
        lines = ["        '%s': '%s',\n" % (k, v) for k, v in flow.request.query]
        params = "\n    params = {\n%s    }\n" % "".join(lines)
        args += "\n        params=params,"

    data = ""
    if flow.request.body:
        data = "\n    data = '''%s'''\n" % flow.request.body
        args += "\n        data=data,"

    code = code.format(
        name=name,
        url=url,
        headers=headers,
        params=params,
        data=data,
        method=flow.request.method,
        args=args,
    )

    host = flow.request.scheme + "://" + flow.request.host
    code = code.replace(host, "' + self.locust.host +'")
    code = code.replace(urllib.quote_plus(host), "' + urllib.quote_plus(self.locust.host) +'")
    code = code.replace(urllib.quote(host), "' + urllib.quote(self.locust.host) +'")

    code = "\n".join("    " + i for i in code.splitlines())

    return code
