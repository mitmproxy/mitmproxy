#!/usr/bin/env python
from pathod import pathoc

p = pathoc.Pathoc(("google.com", 80))
p.connect()
print p.request("get:/")
print p.request("get:/foo")
