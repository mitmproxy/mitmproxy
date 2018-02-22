#!/usr/bin/env python

from mitmproxy import flowfilter


print("<table class=\"table filtertable\"><tbody>")
for i in flowfilter.help:
    print("<tr><th>%s</th><td>%s</td></tr>" % i)
print("</tbody></table>")