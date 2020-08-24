#!/usr/bin/env bash

docker build --pull --rm -t mitmproxy-clirecorder:latest .
docker run -i -t --rm --add-host "tutorial.mitm.it:1.1.1.1" \
    -v "$(pwd)"/../../../mitmproxy/addons/tutorialapp/static/recordings:/root/clidirector/recordings \
    mitmproxy-clirecorder:latest
