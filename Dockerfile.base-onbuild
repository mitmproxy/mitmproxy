FROM debian:jessie

ENV DEBIAN_FRONTEND noninteractive
ENV PYTHON /usr/bin/python2.7

RUN apt-get update && \
    apt-get install -qq -y --no-install-recommends \
        build-essential \
        python-pip \
        python-dev \
        python-setuptools \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        git \
        zlib1g-dev \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/*

ENV LANG en_US.UTF-8
ENV LC_ALL C.UTF-8

ONBUILD ADD . /opt/mitmproxy
ONBUILD WORKDIR /opt/mitmproxy
ONBUILD RUN [ ! -e requirements.txt ] || pip install -r requirements.txt && \
    rm -rf ~/.cache/pip /tmp/pip_build_root
