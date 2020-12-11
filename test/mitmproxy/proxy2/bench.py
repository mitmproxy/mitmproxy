"""
Usage:
  - pip install pytest-benchmark
  - pytest bench.py

See also:
  - https://github.com/mitmproxy/proxybench
"""
import copy

from .layers import test_tcp, test_tls
from .layers.http import test_http, test_http2


def test_bench_http_roundtrip(tctx, benchmark):
    # benchmark something
    benchmark(test_http.test_http_proxy, tctx)


def test_bench_http2_roundtrip(tctx, benchmark):
    # benchmark something
    benchmark(test_http2.test_simple, tctx)


def test_bench_tcp_roundtrip(tctx, benchmark):
    # benchmark something
    benchmark(lambda: test_tcp.test_simple(copy.deepcopy(tctx)))


def test_bench_server_tls(tctx, benchmark):
    t = test_tls.TestServerTLS().test_simple
    benchmark(lambda: t(copy.deepcopy(tctx)))


def test_bench_client_tls(tctx, benchmark):
    t = test_tls.TestClientTLS().test_client_only
    benchmark(lambda: t(copy.deepcopy(tctx)))


def test_bench_tls_both(tctx, benchmark):
    t = test_tls.TestClientTLS().test_server_required
    benchmark(lambda: t(copy.deepcopy(tctx)))
