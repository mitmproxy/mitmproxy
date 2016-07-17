from __future__ import absolute_import, print_function, division

import json
import re
from textwrap import dedent

import six
from six.moves import urllib

import netlib.http


def _native(s):
    if six.PY2:
        if isinstance(s, six.text_type):
            return s.encode()
    else:
        if isinstance(s, six.binary_type):
            return s.decode()
    return s


def dictstr(items, indent):
    lines = []
    for k, v in items:
        lines.append(indent + "%s: %s,\n" % (repr(_native(k)), repr(_native(v))))
    return "{\n%s}\n" % "".join(lines)


def curl_command(flow):
    data = "curl "

    request = flow.request.copy()
    request.decode(strict=False)

    for k, v in request.headers.items(multi=True):
        data += "-H '%s:%s' " % (k, v)

    if request.method != "GET":
        data += "-X %s " % request.method

    full_url = request.scheme + "://" + request.host + request.path
    data += "'%s'" % full_url

    if request.content:
        data += " --data-binary '%s'" % _native(request.content)

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

    components = [urllib.parse.quote(c, safe="") for c in flow.request.path_components]
    url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)

    args = ""
    headers = ""
    if flow.request.headers:
        headers += "\nheaders = %s\n" % dictstr(flow.request.headers.fields, "    ")
        args += "\n    headers=headers,"

    params = ""
    if flow.request.query:
        params = "\nparams = %s\n" % dictstr(flow.request.query.collect(), "    ")
        args += "\n    params=params,"

    data = ""
    if flow.request.body:
        json_obj = is_json(flow.request.headers, flow.request.content)
        if json_obj:
            data = "\njson = %s\n" % dictstr(sorted(json_obj.items()), "    ")
            args += "\n    json=json,"
        else:
            data = "\ndata = '''%s'''\n" % _native(flow.request.content)
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


def is_json(headers, content):
    # type: (netlib.http.Headers, bytes) -> bool
    if headers:
        ct = netlib.http.parse_content_type(headers.get("content-type", ""))
        if ct and "%s/%s" % (ct[0], ct[1]) == "application/json":
            try:
                return json.loads(content.decode("utf8", "surrogateescape"))
            except ValueError:
                return False
    return False


def locust_code(flow):
    code = dedent("""
        from locust import HttpLocust, TaskSet, task

        class UserBehavior(TaskSet):
            def on_start(self):
                ''' on_start is called when a Locust start before any task is scheduled '''
                self.{name}()

            @task()
            def {name}(self):
                url = '{url}'
                {headers}{params}{data}
                self.response = self.client.request(
                    method='{method}',
                    url=url,{args}
                )

            ### Additional tasks can go here ###


        class WebsiteUser(HttpLocust):
            task_set = UserBehavior
            min_wait = 1000
            max_wait = 3000
""").strip()

    components = [urllib.parse.quote(c, safe="") for c in flow.request.path_components]
    name = re.sub('\W|^(?=\d)', '_', "_".join(components))
    if name == "" or name is None:
        new_name = "_".join([str(flow.request.host), str(flow.request.timestamp_start)])
        name = re.sub('\W|^(?=\d)', '_', new_name)

    url = flow.request.scheme + "://" + flow.request.host + "/" + "/".join(components)

    args = ""
    headers = ""
    if flow.request.headers:
        lines = [
            (_native(k), _native(v)) for k, v in flow.request.headers.fields
            if _native(k).lower() not in ["host", "cookie"]
        ]
        lines = ["            '%s': '%s',\n" % (k, v) for k, v in lines]
        headers += "\n        headers = {\n%s        }\n" % "".join(lines)
        args += "\n            headers=headers,"

    params = ""
    if flow.request.query:
        lines = ["            %s: %s,\n" % (repr(k), repr(v)) for k, v in flow.request.query.collect()]
        params = "\n        params = {\n%s        }\n" % "".join(lines)
        args += "\n            params=params,"

    data = ""
    if flow.request.content:
        data = "\n        data = '''%s'''\n" % _native(flow.request.content)
        args += "\n            data=data,"

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
    code = code.replace(host, "' + self.locust.host + '")
    code = code.replace(urllib.parse.quote_plus(host), "' + quote_plus(self.locust.host) + '")
    code = code.replace(urllib.parse.quote(host), "' + quote(self.locust.host) + '")
    code = code.replace("'' + ", "")

    return code


def locust_task(flow):
    code = locust_code(flow)
    start_task = len(code.split('@task')[0]) - 4
    end_task = -19 - len(code.split('### Additional')[1])
    task_code = code[start_task:end_task]

    return task_code


def url(flow):
    return flow.request.url


EXPORTERS = [
    ("content", "c", None),
    ("headers+content", "h", None),
    ("url", "u", url),
    ("as curl command", "r", curl_command),
    ("as python code", "p", python_code),
    ("as locust code", "l", locust_code),
    ("as locust task", "t", locust_task),
]
