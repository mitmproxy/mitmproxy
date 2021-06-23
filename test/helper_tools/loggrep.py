#!/usr/bin/env python3
import fileinput
import sys
import re

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} port filenames")
        sys.exit()

    port = sys.argv[1]
    matches = False
    for line in fileinput.input(sys.argv[2:]):
        if re.match(r"^\[|(\d+\.){3}", line):
            matches = port in line
        if matches:
            print(line, end="")
