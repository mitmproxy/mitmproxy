
This directory contains an addon for benchmarking and profiling mitmproxy. At
the moment, this is simply to give developers a quick way to see the impact of
their work. Eventually, this might grow into a performance dashboard with
historical data, so we can track performance over time.

# Setup

Install the following tools:

    https://github.com/wg/wrk

    go get github.com/cortesi/devd/cmd/devd

You may also want to install snakeviz to make viewing profiles easier:

    pip install snakeviz

Now run the benchmark by loading the addon. A typical invocation is as follows:

    mitmdump -p0 -q --set benchmark_save_path=/tmp/foo -s ./benchmark.py

This will start up the backend server, run the benchmark, save the results to
/tmp/foo.bench and /tmp/foo.prof, and exit.
