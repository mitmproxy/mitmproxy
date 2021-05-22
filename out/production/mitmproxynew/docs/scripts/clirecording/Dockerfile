# todo: use a more lightweight base, e.g., Alpine Linux
FROM ubuntu:18.04

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV TERM screen-256color

# install mitmproxy, asciinema, and dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    asciinema \
    autoconf \
    automake \
    autotools-dev \
    bison \
    curl \
    git \
    libevent-dev \
    libtool \
    locales \
    m4 \
    make \
    ncurses-dev \
    pkg-config \
    python3-pip \
    python3 \
    python3-setuptools \
    wget \
    xterm \
    && locale-gen --purge "en_US.UTF-8" \
    && update-locale "LANG=en_US.UTF-8" \
    && pip3 install --no-cache-dir libtmux curl requests mitmproxy \
    && rm -rf /var/lib/apt/lists/*

# install latest tmux (to support popups)
RUN git clone --depth 1 https://github.com/tmux/tmux.git \
    && cd tmux \
    && sh autogen.sh \
    && ./configure && make && make install \
    && cd ../ \
    && rm -rf tmux

WORKDIR /root/clidirector

COPY ./docker/tmux.conf ../.tmux.conf
COPY clidirector.py screenplays.py record.py ./

RUN echo 'PS1="[tutorial@mitmproxy] $ "' >> /root/.bashrc

ENTRYPOINT [ "./record.py" ]
