#!/usr/bin/env bash

docker build --pull --rm -t mitmproxy-clirecorder:latest .
docker run -i -t --rm \
    -v "$(pwd)"/../../src/assets/recordings:/root/clidirector/recordings \
    mitmproxy-clirecorder:latest
