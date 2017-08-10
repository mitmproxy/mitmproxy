import os.path
import shutil

from mitmproxy import ctx
from mitmproxy import flow


class StaticViewer:
    def __init__(self):
        self.active_flows = set() # type: Set[flow.Flow]

    def save(self, path: str) -> None:
        """
            Save the files for the static web view.
        """
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        index_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
        path = os.path.expanduser(path)
        # We want to overwrite the static files to keep track of the update.
        try:
            shutil.copytree(static_path, os.path.join(path, 'static'),
                            ignore=shutil.ignore_patterns('static.js'))
        except FileExistsError:
            shutil.rmtree(os.path.join(path, 'static'))
            shutil.copytree(static_path, os.path.join(path, 'static'),
                            ignore=shutil.ignore_patterns('static.js'))

        index_template = open(index_path, 'r')
        index = open(os.path.join(path, 'index.html'), 'w')
        # Change the resource files to relative path.
        index.write(index_template.read().replace('/static/', './static/'))
        index_template.close()
        index.close()

        static_template = open(os.path.join(static_path, 'static.js'), 'r')
        static = open(os.path.join(path, 'static', 'static.js'), 'w')
        # Turn on MITMWEB_STATIC variable
        static.write(static_template.read().replace('false', 'true'))
        static_template.close()
        static.close()

    def load(self, loader):
        loader.add_option(
            "web_static_viewer", str, "",
            "The path to output a static viewer."
        )

    def configure(self, updated):
        if "web_static_viewer" in updated and ctx.options.web_static_viewer:
            self.save(ctx.options.web_static_viewer)


