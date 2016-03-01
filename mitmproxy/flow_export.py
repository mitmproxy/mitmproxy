import urllib
from textwrap import dedent

import netlib.http
from . import contentviews


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
        cv = contentviews.get_content_view(
            viewmode=contentviews.get("Auto"),
            data=flow.request.body,
            headers=flow.request.headers,
        )

        if cv[0] == "JSON":
            data = "\njson = %s\n" % "\n".join(l[0][1] for l in cv[1])
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
