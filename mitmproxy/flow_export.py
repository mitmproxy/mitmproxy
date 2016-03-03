import json
import urllib
from textwrap import dedent

import netlib.http
from netlib.utils import parse_content_type


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
        json_obj = is_json(flow.request.headers, flow.request.body)
        if json_obj:
            # Without the separators field json.dumps() produces
            # trailing white spaces: https://bugs.python.org/issue16333
            data = json.dumps(json_obj, indent=4, separators=(',', ': '))
            data = "\njson = %s\n" % data
            args += "\n    json=json,"
        else:
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


def is_json(headers, content):
    if headers:
        ct = parse_content_type(headers.get("content-type", ""))
        if ct and "%s/%s" % (ct[0], ct[1]) == "application/json":
            try:
                return json.loads(content)
            except ValueError:
                return False
    return False
