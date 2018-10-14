#!/usr/bin/env python3

from mitmproxy import flowfilter


print("<table class=\"table filtertable\"><tbody>")
for i in flowfilter.help:
    print("<tr><th>%s</th><td>%s</td></tr>" % i)
print("</tbody></table>")
