#!/usr/bin/env python3
import asyncio

from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy.tools import console
from mitmproxy.tools import dump
from mitmproxy.tools import web

masters = {
    "mitmproxy": console.master.ConsoleMaster,
    "mitmdump": dump.DumpMaster,
    "mitmweb": web.master.WebMaster,
}

unified_options = {}


async def dump():
    for tool_name, master in masters.items():
        opts = options.Options()
        _ = master(opts)
        for key, option in optmanager.dump_dicts(opts).items():
            if key in unified_options:
                unified_options[key]["tools"].append(tool_name)
            else:
                unified_options[key] = option
                unified_options[key]["tools"] = [tool_name]


asyncio.run(dump())

print(
    """
      <table class=\"table optiontable\">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
        </thead>
        <tbody>
      """.strip()
)
for key, option in sorted(unified_options.items(), key=lambda t: t[0]):
    print(
        f"""
          <tr id="{key}">
          <th>
            {key}<a class="anchor" href="#{key}"></a><br/>
            {" ".join(["<span class='badge'>{}</span>".format(t) for t in option["tools"]])}</th>
          <td>{option["type"]}</td>
          <td>{option["help"]}<br/>
            Default: {option["default"]}
            {"<br/>Choices: {}".format(", ".join(option["choices"])) if option["choices"] else ""}

          </td>
          </tr>
          """.strip()
    )
print("</tbody></table>")
