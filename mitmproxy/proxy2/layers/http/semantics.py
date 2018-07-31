from mitmproxy.proxy2.layer import Layer


class HTTPLayer(Layer):
    """
    HTTP Semantics layer used by the on-the-wire layers for HTTP/1 and HTTP/2.
    """

    def _handle_event(self, event: HttpEvent):
        if isinstance(event, RequestHeaders):
            yield commands.Log(f"RequestHeadersReceived: {event}")

            # This is blocking only this layer, none of the parent layers.
            yield commands.Hook("requestheaders", event.flow)
            yield commands.Log(f"Hook processed: {event}")

        elif isinstance(event, RequestData):
            raise NotImplementedError
        elif isinstance(event, RequestComplete):
            yield commands.Log(f"RequestComplete: {event}")
            yield commands.Hook("request", event.flow)
            yield commands.Log(f"Hook processed: {event}")
            yield SendRequestHeaders(event.flow)
            # TODO yield SendRequestData()
            yield SendRequestComplete(event.flow)
        elif isinstance(event, ResponseHeaders):
            yield commands.Log(f"ResponseHeadersReceived: {event}")

            # This is blocking only this layer, none of the parent layers.
            yield commands.Hook("responseheaders", event.flow)
            yield commands.Log(f"Hook processed: {event}")

        elif isinstance(event, ResponseData):
            event.flow.response.raw_content = (
                (event.flow.response.raw_content or b"")
                + event.data
            )
        elif isinstance(event, ResponseComplete):
            yield commands.Log(f"ResponseComplete: {event}")
            yield commands.Hook("response", event.flow)
            yield commands.Log(f"Hook processed: {event}")
            yield SendResponseHeaders(event.flow)
            yield SendResponseData(event.flow, event.flow.response.raw_content)
            yield SendResponseComplete(event.flow)

        elif isinstance(event, events.ConnectionClosed):
            yield commands.Log(f"HTTPLayer unimplemented event: {event}", level="error")
        else:
            raise NotImplementedError(event)
