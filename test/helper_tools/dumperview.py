#!/usr/bin/env python3
import click

from mitmproxy.addons import dumper
from mitmproxy.test import tflow
from mitmproxy.test import taddons


def show(flow_detail, flows):
    d = dumper.Dumper()
    with taddons.context() as ctx:
        ctx.configure(d, flow_detail=flow_detail)
        for f in flows:
            ctx.cycle(d, f)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--level', default=1, help='Detail level')
def tcp(level):
    f1 = tflow.ttcpflow(client_conn=True, server_conn=True)
    show(level, [f1])


@cli.command()
@click.option('--level', default=1, help='Detail level')
def large(level):
    f1 = tflow.tflow(client_conn=True, server_conn=True, resp=True)
    f1.response.headers["content-type"] = "text/html"
    f1.response.content = b"foo bar voing\n" * 100
    show(level, [f1])


@cli.command()
@click.option('--level', default=1, help='Detail level')
def small(level):
    f1 = tflow.tflow(client_conn=True, server_conn=True, resp=True)
    f1.response.headers["content-type"] = "text/html"
    f1.response.content = b"<html><body>Hello!</body></html>"

    f2 = tflow.tflow(client_conn=True, server_conn=True, err=True)

    show(
        level,
        [
            f1, f2,
        ]
    )


if __name__ == "__main__":
    cli()
