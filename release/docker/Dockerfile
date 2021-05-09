FROM python:3.9-slim-buster

ARG MITMPROXY_WHEEL

RUN useradd -mU mitmproxy
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY $MITMPROXY_WHEEL /home/mitmproxy/
COPY requirements.txt /home/mitmproxy/
RUN pip3 install --no-cache-dir --require-hashes -r /home/mitmproxy/requirements.txt \
    && pip3 install --no-cache-dir --no-deps /home/mitmproxy/${MITMPROXY_WHEEL} \
    && rm /home/mitmproxy/${MITMPROXY_WHEEL} /home/mitmproxy/requirements.txt

VOLUME /home/mitmproxy/.mitmproxy

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080 8081

CMD ["mitmproxy"]
