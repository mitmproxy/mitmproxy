# todo: use a more lightweight base, e.g., Alpine Linux
FROM ubuntu:18.04

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV TERM screen-256color

# install mitmproxy, asciinema, and dependencies
RUN apt-get update && apt-get install -y \
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
    wget \
    xterm \
    && locale-gen --purge "en_US.UTF-8" \
    && update-locale "LANG=en_US.UTF-8" \
    && pip3 install libtmux curl requests mitmproxy

# install latest tmux (to support popups)
RUN git clone https://github.com/tmux/tmux.git \
    && cd tmux \
    && sh autogen.sh \
    && ./configure && make && make install

WORKDIR /root/clidirector

COPY ./docker/tmux.conf ../.tmux.conf
COPY clidirector.py screenplays.py record.py ./

RUN echo 'PS1="[tutorial@mitmproxy] $ "' >> /root/.bashrc

ENTRYPOINT [ "./record.py" ]
