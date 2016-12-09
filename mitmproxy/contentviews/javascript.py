import jsbeautifier

from . import base


class ViewJavaScript(base.View):
    name = "JavaScript"
    prompt = ("javascript", "j")
    content_types = [
        "application/x-javascript",
        "application/javascript",
        "text/javascript"
    ]

    def __call__(self, data, **metadata):
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        data = data.decode("utf-8", "replace")
        res = jsbeautifier.beautify(data, opts)
        return "JavaScript", base.format_text(res)
