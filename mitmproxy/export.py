import io
import json
import pprint
import re
import textwrap
from typing import Any

from mitmproxy import http


def _native(s):
    if isinstance(s, bytes):
        return s.decode()
    return s


def dictstr(items, indent: str) -> str:
    lines = []
    for k, v in items:
        lines.append(indent + "%s: %s,\n" % (repr(_native(k)), repr(_native(v))))
    return "{\n%s}\n" % "".join(lines)


def curl_command(flow: http.HTTPFlow) -> str:
    data = "curl "

    request = flow.request.copy()
    request.decode(strict=False)

    for k, v in request.headers.items(multi=True):
        data += "-H '%s:%s' " % (k, v)

    if request.method != "GET":
        data += "-X %s " % request.method

    data += "'%s'" % request.url

    if request.content:
        data += " --data-binary '%s'" % _native(request.content)

    return data


def python_arg(arg: str, val: Any) -> str:
    if not val:
        return ""
    if arg:
        arg += "="
    arg_str = "{}{},\n".format(
        arg,
        pprint.pformat(val, 79 - len(arg))
    )
    return textwrap.indent(arg_str, " " * 4)


def python_code(flow: http.HTTPFlow):
    code = io.StringIO()

    def writearg(arg, val):
        code.write(python_arg(arg, val))

    code.write("import requests\n")
    code.write("\n")
    if flow.request.method.lower() in ("get", "post", "put", "head", "delete", "patch"):
        code.write("response = requests.{}(\n".format(flow.request.method.lower()))
    else:
        code.write("response = requests.request(\n")
        writearg("", flow.request.method)
    url_without_query = flow.request.url.split("?", 1)[0]
    writearg("", url_without_query)

    writearg("params", list(flow.request.query.fields))

    headers = flow.request.headers.copy()
    # requests adds those by default.
    for x in ("host", "content-length"):
        headers.pop(x, None)
    writearg("headers", dict(headers))
    try:
        if "json" not in flow.request.headers.get("content-type", ""):
            raise ValueError()
        writearg("json", json.loads(flow.request.text))
    except ValueError:
        writearg("data", flow.request.content)

    code.seek(code.tell() - 2)  # remove last comma
    code.write("\n)\n")
    code.write("\n")
    code.write("print(response.text)")

    return code.getvalue()


def locust_code(flow):
    code = textwrap.dedent("""
        from locust import HttpLocust, TaskSet, task

        class UserBehavior(TaskSet):
            def on_start(self):
                ''' on_start is called when a Locust start before any task is scheduled '''
                self.{name}()

            @task()
            def {name}(self):
                url = self.locust.host + '{path}'
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

    name = re.sub('\W|^(?=\d)', '_', flow.request.path.strip("/").split("?", 1)[0])
    if not name:
        new_name = "_".join([str(flow.request.host), str(flow.request.timestamp_start)])
        name = re.sub('\W|^(?=\d)', '_', new_name)

    path_without_query = flow.request.path.split("?")[0]

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
        lines = [
            "            %s: %s,\n" % (repr(k), repr(v))
            for k, v in
            flow.request.query.collect()
        ]
        params = "\n        params = {\n%s        }\n" % "".join(lines)
        args += "\n            params=params,"

    data = ""
    if flow.request.content:
        data = "\n        data = '''%s'''\n" % _native(flow.request.content)
        args += "\n            data=data,"

    code = code.format(
        name=name,
        path=path_without_query,
        headers=headers,
        params=params,
        data=data,
        method=flow.request.method,
        args=args,
    )

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
