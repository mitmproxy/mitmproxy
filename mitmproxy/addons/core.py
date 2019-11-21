import typing

import os

from mitmproxy.utils import human
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import optmanager
from mitmproxy import platform
from mitmproxy.net import server_spec
from mitmproxy.net.http import status_codes
import mitmproxy.types


CONF_DIR = "~/.mitmproxy"
LISTEN_PORT = 8080


class Core:
    def load(self, loader):
        loader.add_option(
            "body_size_limit", typing.Optional[str], None,
            """
            Byte size limit of HTTP request and response bodies. Understands
            k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        loader.add_option(
            "keep_host_header", bool, False,
            """
            Reverse Proxy: Keep the original host header instead of rewriting it
            to the reverse proxy target.
            """
        )

    def configure(self, updated):
        opts = ctx.options
        if opts.add_upstream_certs_to_client_chain and not opts.upstream_cert:
            raise exceptions.OptionsError(
                "The no-upstream-cert and add-upstream-certs-to-client-chain "
                "options are mutually exclusive. If no-upstream-cert is enabled "
                "then the upstream certificate is not retrieved before generating "
                "the client certificate chain."
            )
        if opts.add_upstream_certs_to_client_chain and not opts.ssl_insecure:
            raise exceptions.OptionsError(
                "The verify-upstream-cert requires certificate verification to be disabled. "
                "If upstream certificates are verified then extra upstream certificates are "
                "not available for inclusion to the client chain."
            )
        if "body_size_limit" in updated:
            try:
                human.parse_size(opts.body_size_limit)
            except ValueError:
                raise exceptions.OptionsError(
                    "Invalid body size limit specification: %s" %
                    opts.body_size_limit
                )
        if "mode" in updated:
            mode = opts.mode
            if mode.startswith("reverse:") or mode.startswith("upstream:"):
                try:
                    server_spec.parse_with_mode(mode)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
            elif mode == "transparent":
                if not platform.original_addr:
                    raise exceptions.OptionsError(
                        "Transparent mode not supported on this platform."
                    )
            elif mode not in ["regular", "socks5"]:
                raise exceptions.OptionsError(
                    "Invalid mode specification: %s" % mode
                )
        if "client_certs" in updated:
            if opts.client_certs:
                client_certs = os.path.expanduser(opts.client_certs)
                if not os.path.exists(client_certs):
                    raise exceptions.OptionsError(
                        "Client certificate path does not exist: {}".format(opts.client_certs)
                    )

    @command.command("set")
    def set(self, option: str, value: str = "") -> None:
        """
            Set an option. When the value is omitted, booleans are set to true,
            strings and integers are set to None (if permitted), and sequences
            are emptied. Boolean values can be true, false or toggle.
            Multiple values are concatenated with a single space.
        """
        strspec = f"{option}={value}"
        try:
            ctx.options.set(strspec)
        except exceptions.OptionsError as e:
            raise exceptions.CommandError(e) from e

    @command.command("flow.resume")
    def resume(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Resume flows if they are intercepted.
        """
        intercepted = [i for i in flows if i.intercepted]
        for f in intercepted:
            f.resume()
        ctx.master.addons.trigger("update", intercepted)

    # FIXME: this will become view.mark later
    @command.command("flow.mark")
    def mark(self, flows: typing.Sequence[flow.Flow], boolean: bool) -> None:
        """
            Mark flows.
        """
        updated = []
        for i in flows:
            if i.marked != boolean:
                i.marked = boolean
                updated.append(i)
        ctx.master.addons.trigger("update", updated)

    # FIXME: this will become view.mark.toggle later
    @command.command("flow.mark.toggle")
    def mark_toggle(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Toggle mark for flows.
        """
        for i in flows:
            i.marked = not i.marked
        ctx.master.addons.trigger("update", flows)

    @command.command("flow.kill")
    def kill(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Kill running flows.
        """
        updated = []
        for f in flows:
            if f.killable:
                f.kill()
                updated.append(f)
        ctx.log.alert("Killed %s flows." % len(updated))
        ctx.master.addons.trigger("update", updated)

    # FIXME: this will become view.revert later
    @command.command("flow.revert")
    def revert(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Revert flow changes.
        """
        updated = []
        for f in flows:
            if f.modified():
                f.revert()
                updated.append(f)
        ctx.log.alert("Reverted %s flows." % len(updated))
        ctx.master.addons.trigger("update", updated)

    @command.command("flow.set.options")
    def flow_set_options(self) -> typing.Sequence[str]:
        return [
            "host",
            "status_code",
            "method",
            "path",
            "url",
            "reason",
        ]

    @command.command("flow.set")
    @command.argument("attr", type=mitmproxy.types.Choice("flow.set.options"))
    def flow_set(
        self,
        flows: typing.Sequence[flow.Flow],
        attr: str,
        value: str
    ) -> None:
        """
            Quickly set a number of common values on flows.
        """
        val: typing.Union[int, str] = value
        if attr == "status_code":
            try:
                val = int(val)  # type: ignore
            except ValueError as v:
                raise exceptions.CommandError(
                    "Status code is not an integer: %s" % val
                ) from v

        updated = []
        for f in flows:
            req = getattr(f, "request", None)
            rupdate = True
            if req:
                if attr == "method":
                    req.method = val
                elif attr == "host":
                    req.host = val
                elif attr == "path":
                    req.path = val
                elif attr == "url":
                    try:
                        req.url = val
                    except ValueError as e:
                        raise exceptions.CommandError(
                            "URL %s is invalid: %s" % (repr(val), e)
                        ) from e
                else:
                    self.rupdate = False

            resp = getattr(f, "response", None)
            supdate = True
            if resp:
                if attr == "status_code":
                    resp.status_code = val
                    if val in status_codes.RESPONSES:
                        resp.reason = status_codes.RESPONSES[val]  # type: ignore
                elif attr == "reason":
                    resp.reason = val
                else:
                    supdate = False

            if rupdate or supdate:
                updated.append(f)

        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Set %s on  %s flows." % (attr, len(updated)))

    @command.command("flow.decode")
    def decode(self, flows: typing.Sequence[flow.Flow], part: str) -> None:
        """
            Decode flows.
        """
        updated = []
        for f in flows:
            p = getattr(f, part, None)
            if p:
                f.backup()
                p.decode()
                updated.append(f)
        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Decoded %s flows." % len(updated))

    @command.command("flow.encode.toggle")
    def encode_toggle(self, flows: typing.Sequence[flow.Flow], part: str) -> None:
        """
            Toggle flow encoding on and off, using deflate for encoding.
        """
        updated = []
        for f in flows:
            p = getattr(f, part, None)
            if p:
                f.backup()
                current_enc = p.headers.get("content-encoding", "identity")
                if current_enc == "identity":
                    p.encode("deflate")
                else:
                    p.decode()
                updated.append(f)
        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Toggled encoding on %s flows." % len(updated))

    @command.command("flow.encode")
    @command.argument("encoding", type=mitmproxy.types.Choice("flow.encode.options"))
    def encode(
        self,
        flows: typing.Sequence[flow.Flow],
        part: str,
        encoding: str,
    ) -> None:
        """
            Encode flows with a specified encoding.
        """
        updated = []
        for f in flows:
            p = getattr(f, part, None)
            if p:
                current_enc = p.headers.get("content-encoding", "identity")
                if current_enc == "identity":
                    f.backup()
                    p.encode(encoding)
                    updated.append(f)
        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Encoded %s flows." % len(updated))

    @command.command("flow.encode.options")
    def encode_options(self) -> typing.Sequence[str]:
        """
            The possible values for an encoding specification.
        """
        return ["gzip", "deflate", "br", "zstd"]

    @command.command("options.load")
    def options_load(self, path: mitmproxy.types.Path) -> None:
        """
            Load options from a file.
        """
        try:
            optmanager.load_paths(ctx.options, path)
        except (OSError, exceptions.OptionsError) as e:
            raise exceptions.CommandError(
                "Could not load options - %s" % e
            ) from e

    @command.command("options.save")
    def options_save(self, path: mitmproxy.types.Path) -> None:
        """
            Save options to a file.
        """
        try:
            optmanager.save(ctx.options, path)
        except OSError as e:
            raise exceptions.CommandError(
                "Could not save options - %s" % e
            ) from e

    @command.command("options.reset")
    def options_reset(self) -> None:
        """
            Reset all options to defaults.
        """
        ctx.options.reset()

    @command.command("options.reset.one")
    def options_reset_one(self, name: str) -> None:
        """
            Reset one option to its default value.
        """
        if name not in ctx.options:
            raise exceptions.CommandError("No such option: %s" % name)
        setattr(
            ctx.options,
            name,
            ctx.options.default(name),
        )
