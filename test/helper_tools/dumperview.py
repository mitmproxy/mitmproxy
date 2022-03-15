#!/usr/bin/env python3
import asyncio
import click

from mitmproxy.addons import dumper
from mitmproxy.test import tflow
from mitmproxy.test import taddons


def run_async(coro):
    """
        Run the given async function in a new event loop.
        This allows async functions to be called synchronously.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def show(flow_detail, flows):
    d = dumper.Dumper()
    with taddons.context() as ctx:
        ctx.configure(d, flow_detail=flow_detail)
        for f in flows:
            run_async(ctx.cycle(d, f))


@click.group()
def cli():
    pass


@cli.command()
@click.option('--level', default=1, help='Detail level')
def tcp(level):
    f1 = tflow.ttcpflow()
    show(level, [f1])


@cli.command()
@click.option('--level', default=1, help='Detail level')
def large(level):
    f1 = tflow.tflow(resp=True)
    f1.response.headers["content-type"] = "text/html"
    f1.response.content = b"foo bar voing\n" * 100
    show(level, [f1])


@cli.command()
@click.option('--level', default=1, help='Detail level')
def small(level):
    f1 = tflow.tflow(resp=True)
    f1.response.headers["content-type"] = "text/html"
    f1.response.content = b"<html><body>Hello!</body></html>"

    f2 = tflow.tflow(err=True)

    show(
        level,
        [
            f1, f2,
        ]
    )


if __name__ == "__main__":
    cli()
