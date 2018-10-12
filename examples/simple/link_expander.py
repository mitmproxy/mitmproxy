# This script determines if request is an HTML webpage and if so seeks out
# relative links (<a href="./about.html">) and expands them to absolute links
# In practice this can be used to front an indexing spider that may not have the capability to expand relative page links.
# Usage: mitmdump -s link_expander.py or mitmproxy -s link_expander.py

import re
from urllib.parse import urljoin


def response(flow):

    if "Content-Type" in flow.response.headers and flow.response.headers["Content-Type"].find("text/html") != -1:
        pageUrl = flow.request.url
        pageText = flow.response.text
        pattern = (r"<a\s+(?:[^>]*?\s+)?href=(?P<delimiter>[\"'])"
                   r"(?P<link>(?!https?:\/\/|ftps?:\/\/|\/\/|#|javascript:|mailto:).*?)(?P=delimiter)")
        rel_matcher = re.compile(pattern, flags=re.IGNORECASE)
        rel_matches = rel_matcher.finditer(pageText)
        map_dict = {}
        for match_num, match in enumerate(rel_matches):
            (delimiter, rel_link) = match.group("delimiter", "link")
            abs_link = urljoin(pageUrl, rel_link)
            map_dict["{0}{1}{0}".format(delimiter, rel_link)] = "{0}{1}{0}".format(delimiter, abs_link)
        for map in map_dict.items():
            pageText = pageText.replace(*map)
            # Uncomment the following to print the expansion mapping
            # print("{0} -> {1}".format(*map))
        flow.response.text = pageText