from typing import List  # noqa

from . import base


class ViewQuery(base.View):
    name = "Query"

    def __call__(self, data, **metadata):
        query = metadata.get("query")
        if query:
            return "Query", base.format_dict(query)
        else:
            return "Query", base.format_text("")
