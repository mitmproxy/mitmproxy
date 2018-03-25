#!/usr/bin/env python3

from mitmproxy import options, optmanager
from mitmproxy.tools import dump, console, web

masters = {
    "mitmproxy": console.master.ConsoleMaster,
    "mitmdump": dump.DumpMaster,
    "mitmweb": web.master.WebMaster
}

unified_options = {}

for tool_name, master in masters.items():
    opts = options.Options()
    inst = master(opts)
    for key, option in optmanager.dump_dicts(opts).items():
        if key in unified_options:
            unified_options[key]['tools'].append(tool_name)
        else:
            unified_options[key] = option
            unified_options[key]['tools'] = [tool_name]

print("""
      <table class=\"table optiontable\">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Description</th>
        </tr>
        </thead>
        <tbody>
      """.strip())
for key, option in sorted(unified_options.items(), key=lambda t: t[0]):
    print("""
          <tr>
          <th>{}<br/>{}</th>
          <td>{}</td>
          <td>{}<br/>
            Default: {}
            {}
          </td>
          </tr>
          """.strip().format(
              key,
              ' '.join(["<span class='badge'>{}</span>".format(t) for t in option['tools']]),
              option['type'],
              option['help'],
              option['default'],
              "<br/>Choices: {}".format(', '.join(option['choices'])) if option['choices'] else "",
    ))
print("</tbody></table>")
