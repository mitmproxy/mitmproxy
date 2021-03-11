FROM python:3.9-slim-buster

ARG WHEEL_MITMPROXY
ARG WHEEL_BASENAME_MITMPROXY

RUN useradd -mU mitmproxy
RUN apt-get update \
    && apt-get install -y gosu \
    && rm -rf /var/lib/apt/lists/*
    
COPY $WHEEL_MITMPROXY /home/mitmproxy/
RUN pip3 install --no-cache-dir -U /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY} \
    && rm -rf /home/mitmproxy/${WHEEL_BASENAME_MITMPROXY}

VOLUME /home/mitmproxy/.mitmproxy

COPY release/docker/docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080 8081

CMD ["mitmproxy"]
