FROM python:3.14-trixie AS wheelbuilder

COPY mitmproxy-*-py3-none-any.whl /wheels/
RUN pip install wheel && pip wheel --wheel-dir /wheels /wheels/*.whl

FROM python:3.14-slim-trixie

RUN useradd -mU mitmproxy
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu nano \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /home/mitmproxy/.mitmproxy \
    && chown mitmproxy:mitmproxy /home/mitmproxy/.mitmproxy

# The wheels are bind-mounted from the `wheelbuilder` stage rather than COPYed
# in. A COPY commits them to their own layer, and the `rm -rf /wheels` below it
# could only write a whiteout on top -- a layer that is already committed cannot
# be removed by a later one, so the wheels shipped in every published image. A
# bind mount is never committed to a layer, so there is nothing left to remove.
RUN --mount=type=bind,from=wheelbuilder,source=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels mitmproxy

VOLUME /home/mitmproxy/.mitmproxy

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8080 8081

CMD ["mitmproxy"]
