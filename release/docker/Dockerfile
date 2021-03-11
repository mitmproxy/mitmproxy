FROM python:3.9-buster

ARG WHEEL_MITMPROXY
ARG WHEEL_BASENAME_MITMPROXY

COPY $WHEEL_MITMPROXY /home/mitmproxy/

# Add our user first to make sure the ID get assigned consistently,
# regardless of whatever dependencies get added.
RUN groupadd mitmproxy && useradd mitmproxy -g mitmproxy\
    && apt-get update \
    && apt-get install -y\
        git \
        g++ \
        libffi-dev \
        openssl \
        libssl-dev \
    && python3 -m ensurepip --upgrade \
    && pip3 install -U pip \
    && LDFLAGS=-L/lib pip3 install -U /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY} \
    && apt-get remove --purge -y \
        git \
        g++ \
        libffi-dev \
        libssl-dev \
        python3-dev \
    && apt-get -y autoremove && apt-get -y clean && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache/pip /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY}

VOLUME /home/mitmproxy/.mitmproxy

COPY release/docker/docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080 8081

CMD ["mitmproxy"]