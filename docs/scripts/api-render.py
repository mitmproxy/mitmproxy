#!/usr/bin/env python3
import os
import shutil
import textwrap
from pathlib import Path

import pdoc.render_helpers

here = Path(__file__).parent

if os.environ.get("DOCS_ARCHIVE", False):
    edit_url_map = {}
else:
    edit_url_map = {
        "mitmproxy": "https://github.com/mitmproxy/mitmproxy/blob/main/mitmproxy/",
    }

pdoc.render.configure(
    template_directory=here / "pdoc-template",
    edit_url_map=edit_url_map,
)
# We can't configure Hugo, but we can configure pdoc.
pdoc.render_helpers.formatter.cssclass = "chroma"

modules = [
    "mitmproxy.addonmanager",
    "mitmproxy.certs",
    "mitmproxy.connection",
    "mitmproxy.coretypes.multidict",
    "mitmproxy.flow",
    "mitmproxy.http",
    "mitmproxy.net.server_spec",
    "mitmproxy.proxy.server_hooks",
    "mitmproxy.tcp",
    "mitmproxy.websocket",
    here / ".." / "src" / "generated" / "events.py",
]

pdoc.pdoc(
    *modules,
    output_directory=here / ".." / "src" / "generated" / "api"
)

api_content = here / ".." / "src" / "content" / "api"
if api_content.exists():
    shutil.rmtree(api_content)

api_content.mkdir()

for module in modules:
    if isinstance(module, Path):
        continue
    filename = f"api/{module.replace('.', '/')}.html"
    (api_content / f"{module}.md").write_text(textwrap.dedent(f"""
        ---
        title: "{module}"
        url: "{filename}"

        menu:
            addons:
                parent: 'Event Hooks & API'
        ---

        {{{{< readfile file="/generated/{filename}" >}}}}
        """))

(here / ".." / "src" / "content" / "addons-api.md").touch()
