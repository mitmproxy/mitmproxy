import click

var = None


@click.command()
@click.argument("x")
def start(x):
    global var
    var = x
