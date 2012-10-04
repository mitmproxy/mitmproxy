#!/usr/bin/env python
from libpathod import pathoc

p = pathoc.Pathoc("google.com", 80)
p.connect()
print p.request("get:/")
