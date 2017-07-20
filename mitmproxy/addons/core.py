import typing

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import optmanager
from mitmproxy.net.http import status_codes


class Core:
    @command.command("set")
    def set(self, *spec: str) -> None:
        """
            Set an option of the form "key[=value]". When the value is omitted,
            booleans are set to true, strings and integers are set to None (if
            permitted), and sequences are emptied. Boolean values can be true,
            false or toggle. If multiple specs are passed, they are joined
            into one separated by spaces.
        """
        strspec = " ".join(spec)
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
    def mark(self, flows: typing.Sequence[flow.Flow], val: bool) -> None:
        """
            Mark flows.
        """
        updated = []
        for i in flows:
            if i.marked != val:
                i.marked = val
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
    def flow_set(
        self,
        flows: typing.Sequence[flow.Flow], spec: str, sval: str
    ) -> None:
        """
            Quickly set a number of common values on flows.
        """
        opts = self.flow_set_options()
        if spec not in opts:
            raise exceptions.CommandError(
                "Set spec must be one of: %s." % ", ".join(opts)
            )

        val = sval  # type: typing.Union[int, str]
        if spec == "status_code":
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
                if spec == "method":
                    req.method = val
                elif spec == "host":
                    req.host = val
                elif spec == "path":
                    req.path = val
                elif spec == "url":
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
                if spec == "status_code":
                    resp.status_code = val
                    if val in status_codes.RESPONSES:
                        resp.reason = status_codes.RESPONSES[val]  # type: ignore
                elif spec == "reason":
                    resp.reason = val
                else:
                    supdate = False

            if rupdate or supdate:
                updated.append(f)

        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Set %s on  %s flows." % (spec, len(updated)))

    @command.command("flow.decode")
    def decode(self, flows: typing.Sequence[flow.Flow], part: str) -> None:
        """
            Decode flows.
        """
        updated = []
        for f in flows:
            p = getattr(f, part, None)
            if p:
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
                current_enc = p.headers.get("content-encoding", "identity")
                if current_enc == "identity":
                    p.encode("deflate")
                else:
                    p.decode()
                updated.append(f)
        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Toggled encoding on %s flows." % len(updated))

    @command.command("flow.encode")
    def encode(self, flows: typing.Sequence[flow.Flow], part: str, enc: str) -> None:
        """
            Encode flows with a specified encoding.
        """
        if enc not in self.encode_options():
            raise exceptions.CommandError("Invalid encoding format: %s" % enc)

        updated = []
        for f in flows:
            p = getattr(f, part, None)
            if p:
                current_enc = p.headers.get("content-encoding", "identity")
                if current_enc == "identity":
                    p.encode(enc)
                    updated.append(f)
        ctx.master.addons.trigger("update", updated)
        ctx.log.alert("Encoded %s flows." % len(updated))

    @command.command("flow.encode.options")
    def encode_options(self) -> typing.Sequence[str]:
        """
            The possible values for an encoding specification.

        """
        return ["gzip", "deflate", "br"]

    @command.command("options.load")
    def options_load(self, path: str) -> None:
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
    def options_save(self, path: str) -> None:
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
