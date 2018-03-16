
This directory contains a set of tools for benchmarking and profiling mitmproxy.
At the moment, this is simply to give developers a quick way to see the impact
of their work. Eventually, this might grow into a performance dashboard with
historical data, so we can track performance over time.


# Setup

Install the following tools:

    go get -u github.com/rakyll/hey
    go get github.com/cortesi/devd/cmd/devd

You may also want to install snakeviz to make viewing profiles easier:

    pip install snakeviz

In one window, run the devd server:

    ./backend


# Running tests

Each run consists of two files - a mitproxy invocation, and a traffic generator.
Make sure the backend is started, then run the proxy:

    ./simple.mitmproxy

Now run the traffic generator:

    ./simple.traffic

After the run is done, quit the proxy with ctrl-c.


# Reading results

Results are placed in the ./results directory. You should see two files - a
performance log from **hey**, and a profile. You can view the profile like so:

    snakeviz ./results/simple.prof













