from mitmproxy import ctx, connection
from mitmproxy.proxy import context, tunnel, layer, events, commands


class DTLSLayer(tunnel.TunnelLayer):
    def __init__(self, context: context.Context):
        super().__init__(
            context,
            tunnel_connection=context.server,
            conn=context.server,
        )

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):  # we need an upstream connection
            if self.tunnel_connection.state is connection.ConnectionState.CLOSED:
                yield commands.OpenConnection(self.tunnel_connection)
        if isinstance(event, events.DataReceived):
            ctx.log.info(f"Event: {event}")
            if event.connection == self.context.client:
                cmd = commands.SendData(self.tunnel_connection, event.data)
            else:
                cmd = commands.SendData(self.context.client, event.data)
            ctx.log.info(f"Command: {commands.SendData(self.context.client, event.data)}")
            yield cmd
        else:
            ctx.log.info(f"Other Event: {event}")
            yield from super()._handle_event(event)
