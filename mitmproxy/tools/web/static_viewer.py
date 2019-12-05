import json
import os.path
import pathlib
import shutil
import time
import typing

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import flowfilter
from mitmproxy import io, flow
from mitmproxy import version
from mitmproxy.tools.web.app import flow_to_json

web_dir = pathlib.Path(__file__).absolute().parent


def save_static(path: pathlib.Path) -> None:
    """
    Save the files for the static web view.
    """
    # We want to overwrite the static files to keep track of the update.
    if (path / "static").exists():
        shutil.rmtree(str(path / "static"))
    shutil.copytree(str(web_dir / "static"), str(path / "static"))
    shutil.copyfile(str(web_dir / 'templates' / 'index.html'), str(path / "index.html"))

    with open(str(path / "static" / "static.js"), "w") as f:
        f.write("MITMWEB_STATIC = true;")


def save_filter_help(path: pathlib.Path) -> None:
    with open(str(path / 'filter-help.json'), 'w') as f:
        json.dump(dict(commands=flowfilter.help), f)


def save_settings(path: pathlib.Path) -> None:
    with open(str(path / 'settings.json'), 'w') as f:
        json.dump(dict(version=version.VERSION), f)


def save_flows(path: pathlib.Path, flows: typing.Iterable[flow.Flow]) -> None:
    with open(str(path / 'flows.json'), 'w') as f:
        json.dump(
            [flow_to_json(f) for f in flows],
            f
        )


def save_flows_content(path: pathlib.Path, flows: typing.Iterable[flow.Flow]) -> None:
    for f in flows:
        for m in ('request', 'response'):
            message = getattr(f, m)
            message_path = path / "flows" / f.id / m
            os.makedirs(str(message_path / "content"), exist_ok=True)

            with open(str(message_path / 'content.data'), 'wb') as content_file:
                # don't use raw_content here as this is served with a default content type
                if message:
                    content_file.write(message.content)
                else:
                    content_file.write(b'No content.')

            # content_view
            t = time.time()
            if message:
                description, lines, error = contentviews.get_message_content_view(
                    'Auto', message, f
                )
            else:
                description, lines = 'No content.', []
            if time.time() - t > 0.1:
                ctx.log(
                    "Slow content view: {} took {}s".format(
                        description.strip(),
                        round(time.time() - t, 1)
                    ),
                    "info"
                )
            with open(str(message_path / "content" / "Auto.json"), "w") as content_view_file:
                json.dump(
                    dict(lines=list(lines), description=description),
                    content_view_file
                )


class StaticViewer:
    # TODO: make this a command at some point.
    def load(self, loader):
        loader.add_option(
            "web_static_viewer", typing.Optional[str], "",
            "The path to output a static viewer."
        )

    def configure(self, updated):
        if "web_static_viewer" in updated and ctx.options.web_static_viewer:
            flows = io.read_flows_from_paths([ctx.options.rfile])
            p = pathlib.Path(ctx.options.web_static_viewer).expanduser()
            self.export(p, flows)

    def export(self, path: pathlib.Path, flows: typing.Iterable[flow.Flow]) -> None:
        save_static(path)
        save_filter_help(path)
        save_flows(path, flows)
        save_flows_content(path, flows)
