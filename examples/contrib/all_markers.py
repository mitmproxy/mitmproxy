from mitmproxy import ctx, command
from mitmproxy.utils import emoji


@command.command('all.markers')
def all_markers():
    'Create a new flow showing all marker values'
    for marker in emoji.emoji:
        ctx.master.commands.call('view.flows.create', 'get', f'https://example.com/{marker}')
        ctx.master.commands.call('flow.mark', [ctx.master.view.focus.flow], marker)
