import logging
import re
from collections.abc import Sequence
from json import dumps

from mitmproxy import command
from mitmproxy import flow

MARKER = ":mag:"
RESULTS_STR = "Search Results: "


class Search:
    def __init__(self):
        self.exp = None

    @command.command("search")
    def _search(self, flows: Sequence[flow.Flow], regex: str) -> None:
        """
        Defines a command named "search" that matches
        the given regular expression against most parts
        of each request/response included in the selected flows.

        Usage: from the flow list view, type ":search" followed by
        a space, then a flow selection expression; e.g., "@shown",
        then the desired regular expression to perform the search.

        Alternatively, define a custom shortcut in keys.yaml; e.g.:
        -
          key: "/"
          ctx: ["flowlist"]
          cmd: "console.command search @shown "

        Flows containing matches to the expression will be marked
        with the magnifying glass emoji, and their comments will
        contain JSON-formatted search results.

        To view flow comments, enter the flow view
        and navigate to the detail tab.
        """

        try:
            self.exp = re.compile(regex)
        except re.error as e:
            logging.error(e)
            return

        for _flow in flows:
            # Erase previous results while preserving other comments:
            comments = list()
            for c in _flow.comment.split("\n"):
                if c.startswith(RESULTS_STR):
                    break
                comments.append(c)
            _flow.comment = "\n".join(comments)

            if _flow.marked == MARKER:
                _flow.marked = False

            results = {k: v for k, v in self.flow_results(_flow).items() if v}
            if results:
                comments.append(RESULTS_STR)
                comments.append(dumps(results, indent=2))
                _flow.comment = "\n".join(comments)
                _flow.marked = MARKER

    def header_results(self, message):
        results = {k: self.exp.findall(v) for k, v in message.headers.items()}
        return {k: v for k, v in results.items() if v}

    def flow_results(self, _flow):
        results = dict()
        results.update({"flow_comment": self.exp.findall(_flow.comment)})
        if _flow.request is not None:
            results.update({"request_path": self.exp.findall(_flow.request.path)})
            results.update({"request_headers": self.header_results(_flow.request)})
            if _flow.request.text:
                results.update({"request_body": self.exp.findall(_flow.request.text)})
        if _flow.response is not None:
            results.update({"response_headers": self.header_results(_flow.response)})
            if _flow.response.text:
                results.update({"response_body": self.exp.findall(_flow.response.text)})
        return results


addons = [Search()]
