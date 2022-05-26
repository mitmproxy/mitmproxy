import base64
import binascii
import socket
from typing import Any, Optional

from ntlm_auth import gss_channel_bindings, ntlm

from mitmproxy import addonmanager, http
from mitmproxy import ctx
from mitmproxy.net.http import http1
from mitmproxy.proxy import commands, layer
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layers.http import HttpConnectUpstreamHook, HttpLayer, HttpStream
from mitmproxy.proxy.layers.http._upstream_proxy import HttpUpstreamProxy


class NTLMUpstreamAuth:
    """
        This addon handles authentication to systems upstream from us for the
        upstream proxy and reverse proxy mode. There are 3 cases:
        - Upstream proxy CONNECT requests should have authentication added, and
          subsequent already connected requests should not.
        - Upstream proxy regular requests
        - Reverse proxy regular requests (CONNECT is invalid in this mode)
    """

    def load(self, loader: addonmanager.Loader) -> None:
        ctx.log.info("NTLMUpstreamAuth loader")
        loader.add_option(
            name="upstream_ntlm_auth",
            typespec=Optional[str],
            default=None,
            help="""
            Add HTTP NTLM authentication to upstream proxy requests.
            Format: username:password.
            """
        )
        loader.add_option(
            name="upstream_ntlm_domain",
            typespec=Optional[str],
            default=None,
            help="""
            Add HTTP NTLM domain for authentication to upstream proxy requests.
            """
        )
        loader.add_option(
            name="upstream_proxy_address",
            typespec=Optional[str],
            default=None,
            help="""
                upstream poxy address.
                """
        )
        loader.add_option(
            name="upstream_ntlm_compatibility",
            typespec=int,
            default=3,
            help="""
            Add HTTP NTLM compatibility for authentication to upstream proxy requests.
            Valid values are 0-5 (Default: 3)
            """
        )
        ctx.log.debug("AddOn: NTLM Upstream Authentication - Loaded")

    def running(self):
        def extract_flow_from_context(context: Context) -> http.HTTPFlow:
            if context and context.layers:
                for l in context.layers:
                    if isinstance(l, HttpLayer):
                        for _, stream in l.streams.items():
                            return stream.flow if isinstance(stream, HttpStream) else None

        def build_connect_flow(context: Context, connect_header: tuple) -> http.HTTPFlow:
            flow = extract_flow_from_context(context)
            if not flow:
                ctx.log.error("failed to build connect flow")
                raise
            flow.request.content = b""  # we should send empty content for handshake
            header_name, header_value = connect_header
            flow.request.headers.add(header_name, header_value)
            return flow

        def patched_start_handshake(self) -> layer.CommandGenerator[None]:
            assert self.conn.address
            self.ntlm_context = CustomNTLMContext(ctx)
            proxy_authorization = self.ntlm_context.get_ntlm_start_negotiate_message()
            self.flow = build_connect_flow(self.context, ("Proxy-Authorization", proxy_authorization))
            yield HttpConnectUpstreamHook(self.flow)
            raw = http1.assemble_request(self.flow.request)
            yield commands.SendData(self.tunnel_connection, raw)

        def extract_proxy_authenticate_msg(response_head: list) -> str:
            for header in response_head:
                if b'Proxy-Authenticate' in header:
                    challenge_message = str(bytes(header).decode('utf-8'))
                    try:
                        token = challenge_message.split(': ')[1]
                    except IndexError:
                        ctx.log.error("Failed to extract challenge_message")
                        raise
                    return token

        def patched_receive_handshake_data(self, data) -> layer.CommandGenerator[tuple[bool, Optional[str]]]:
            self.buf += data
            response_head = self.buf.maybe_extract_lines()
            if response_head:
                response_head = [bytes(x) for x in response_head]
                try:
                    response = http1.read_response_head(response_head)
                except ValueError:
                    return True, None
                challenge_message = extract_proxy_authenticate_msg(response_head)
                if 200 <= response.status_code < 300:
                    if self.buf:
                        yield from self.receive_data(data)
                        del self.buf
                    return True, None
                else:
                    if not challenge_message:
                        return True, None
                    proxy_authorization = self.ntlm_context.get_ntlm_challenge_response_message(challenge_message)
                    self.flow = build_connect_flow(self.context, ("Proxy-Authorization", proxy_authorization))
                    raw = http1.assemble_request(self.flow.request)
                    yield commands.SendData(self.tunnel_connection, raw)
                    return False, None
            else:
                return False, None

        HttpUpstreamProxy.start_handshake = patched_start_handshake
        HttpUpstreamProxy.receive_handshake_data = patched_receive_handshake_data

    def done(self):
        ctx.log.info('close ntlm session')


addons = [
    NTLMUpstreamAuth()
]


class CustomNTLMContext:
    def __init__(self,
                 ctx,
                 preferred_type: str = 'NTLM',
                 cbt_data: gss_channel_bindings.GssChannelBindingsStruct = None):
        # TODO:// take care the cbt_data
        auth: str = ctx.options.upstream_ntlm_auth
        domain: str = str(ctx.options.upstream_ntlm_domain).upper()
        ntlm_compatibility: int = ctx.options.upstream_ntlm_compatibility
        username, password = tuple(auth.split(":"))
        workstation = socket.gethostname().upper()
        ctx.log.debug(f'\nntlm context with the details: "{domain}\\{username}", *****')
        self.ctx_log = ctx.log
        self.preferred_type = preferred_type
        self.ntlm_context = ntlm.NtlmContext(
            username=username,
            password=password,
            domain=domain,
            workstation=workstation,
            ntlm_compatibility=ntlm_compatibility,
            cbt_data=cbt_data)

    def get_ntlm_start_negotiate_message(self) -> str:
        negotiate_message = self.ntlm_context.step()
        negotiate_message_base_64_in_bytes = base64.b64encode(negotiate_message)
        negotiate_message_base_64_ascii = negotiate_message_base_64_in_bytes.decode("ascii")
        negotiate_message_base_64_final = f'{self.preferred_type} {negotiate_message_base_64_ascii}'
        self.ctx_log.debug(
            f'{self.preferred_type} Authentication, negotiate message: {negotiate_message_base_64_final}'
        )
        return negotiate_message_base_64_final

    def get_ntlm_challenge_response_message(self, challenge_message: str) -> Any:
        challenge_message = challenge_message.replace(self.preferred_type + " ", "", 1)
        try:
            challenge_message_ascii_bytes = base64.b64decode(challenge_message, validate=True)
        except binascii.Error as err:
            self.ctx_log.debug(f'{self.preferred_type} Authentication fail with error {err.__str__()}')
            return False
        authenticate_message = self.ntlm_context.step(challenge_message_ascii_bytes)
        negotiate_message_base_64 = '{} {}'.format(self.preferred_type,
                                                   base64.b64encode(authenticate_message).decode('ascii'))
        self.ctx_log.debug(
            f'{self.preferred_type} Authentication, response to challenge message: {negotiate_message_base_64}'
        )
        return negotiate_message_base_64
