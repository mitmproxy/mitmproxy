import click

var = None


@click.command()
@click.pass_obj
def start(context):
    global var
    var = context
