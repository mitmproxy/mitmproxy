import os.path
import shutil
import json
from typing import Optional

from mitmproxy import io
from mitmproxy import ctx
from mitmproxy import flowfilter
from mitmproxy import contentviews
from mitmproxy.tools.web.app import flow_to_json


class StaticViewer:
    def __init__(self):
        self.flows = set()  # type: Set[flow.Flow]
        self.path = ''
        self.flows_path = ''

    def load(self, loader):
        loader.add_option(
            "web_static_viewer", Optional[str], "",
            "The path to output a static viewer."
        )

    def configure(self, updated):
        if "web_static_viewer" in updated and ctx.options.web_static_viewer:
            self.path = os.path.expanduser(ctx.options.web_static_viewer)
        if "rfile" in updated and ctx.options.rfile:
            self.flows_path = os.path.expanduser(ctx.options.rfile)

        if self.flows_path and self.path:
            self.save_static()
            self.load_flows()
            self.save_flows()
            self.save_filter_help()
            self.save_flows_content()

    def load_flows(self) -> None:
        with open(self.flows_path, 'rb') as file:
            for i in io.FlowReader(file).stream():
                self.flows.add(i)

    def save_flows(self) -> None:
        with open(os.path.join(self.path, 'flows.json'), 'w') as file:
            flows = []
            for f in self.flows:
                flows.append(flow_to_json(f))
            json.dump(flows, file)

    def save_flows_content(self) -> None:
        for f in self.flows:
            for m in ('request', 'response'):
                message = getattr(f, m)
                path = os.path.join(self.path, 'flows', f.id, m)
                if not os.path.exists(path):
                    os.makedirs(path)
                with open(os.path.join(path, '_content'), 'wb') as content_file:
                    content_file.write(message.raw_content)

                # content_view
                view_path = os.path.join(path, 'content')
                if not os.path.exists(view_path):
                    os.makedirs(view_path)
                description, lines, error = contentviews.get_message_content_view(
                    'Auto', message
                )
                with open(os.path.join(view_path, 'Auto.json'), 'w') as view_file:
                    json.dump(dict(
                        lines=list(lines),
                        description=description
                    ), view_file)

    def save_static(self) -> None:
        """
            Save the files for the static web view.
        """
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        index_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        # We want to overwrite the static files to keep track of the update.
        try:
            shutil.copytree(static_path, os.path.join(self.path, 'static'),
                            ignore=shutil.ignore_patterns('static.js'))
        except FileExistsError:
            shutil.rmtree(os.path.join(self.path, 'static'))
            shutil.copytree(static_path, os.path.join(self.path, 'static'),
                            ignore=shutil.ignore_patterns('static.js'))

        index_template = open(index_path, 'r')
        index = open(os.path.join(self.path, 'index.html'), 'w')
        # Change the resource files to relative path.
        index.write(index_template.read())
        index_template.close()
        index.close()

        static_template = open(os.path.join(static_path, 'static.js'), 'r')
        static = open(os.path.join(self.path, 'static', 'static.js'), 'w')
        # Turn on MITMWEB_STATIC variable
        static.write(static_template.read().replace('false', 'true'))
        static_template.close()
        static.close()

    def save_filter_help(self) -> None:
        with open(os.path.join(self.path, 'filter-help.json'), 'w') as file:
            json.dump(dict(commands=flowfilter.help), file)
