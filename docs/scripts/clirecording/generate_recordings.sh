#!/usr/bin/env bash

docker build --pull --rm -t mitmproxy-clirecorder:latest .
docker run -i -t -v "$(pwd)"/recordings:/root/clidirector/recordings mitmproxy-clirecorder:latest
