FROM resin/raspberrypi3-alpine:3.7

ENV LANG=en_US.UTF-8

ARG WHEEL_MITMPROXY
ARG WHEEL_BASENAME_MITMPROXY

COPY $WHEEL_MITMPROXY /home/mitmproxy/

RUN [ "cross-build-start" ]

# Add our user first to make sure the ID get assigned consistently,
# regardless of whatever dependencies get added.
RUN addgroup -S mitmproxy && adduser -S -G mitmproxy mitmproxy \
    && apk add --no-cache \
        su-exec \
        git \
        g++ \
        libffi \
        libffi-dev \
        libstdc++ \
        openssl \
        openssl-dev \
        python3 \
        python3-dev \
    && python3 -m ensurepip \
    && LDFLAGS=-L/lib pip3 install -U /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY} \
    && apk del --purge \
        git \
        g++ \
        libffi-dev \
        openssl-dev \
        python3-dev \
    && rm -rf ~/.cache/pip /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY}

RUN [ "cross-build-end" ]

VOLUME /home/mitmproxy/.mitmproxy

COPY docker/docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080 8081

CMD ["mitmproxy"]
