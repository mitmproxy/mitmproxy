import contextlib
import functools
import importlib.metadata
import inspect
import logging
import os
import types
from typing import Any

from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import block
from mitmproxy.addons import blocklist
from mitmproxy.addons import browser
from mitmproxy.addons import clientplayback
from mitmproxy.addons import command_history
from mitmproxy.addons import comment
from mitmproxy.addons import core
from mitmproxy.addons import cut
from mitmproxy.addons import disable_h2c
from mitmproxy.addons import dns_resolver
from mitmproxy.addons import export
from mitmproxy.addons import maplocal
from mitmproxy.addons import mapremote
from mitmproxy.addons import modifybody
from mitmproxy.addons import modifyheaders
from mitmproxy.addons import next_layer
from mitmproxy.addons import onboarding
from mitmproxy.addons import proxyauth
from mitmproxy.addons import proxyserver
from mitmproxy.addons import save
from mitmproxy.addons import savehar
from mitmproxy.addons import script
from mitmproxy.addons import serverplayback
from mitmproxy.addons import stickyauth
from mitmproxy.addons import stickycookie
from mitmproxy.addons import strip_dns_https_records
from mitmproxy.addons import tlsconfig
from mitmproxy.addons import update_alt_svc
from mitmproxy.addons import upstream_auth

logger = logging.getLogger(__name__)

BUILTIN_ADDON_CLASSES: tuple[type, ...] = (
    core.Core,
    browser.Browser,
    block.Block,
    strip_dns_https_records.StripDnsHttpsRecords,
    blocklist.BlockList,
    anticache.AntiCache,
    anticomp.AntiComp,
    clientplayback.ClientPlayback,
    command_history.CommandHistory,
    comment.Comment,
    cut.Cut,
    disable_h2c.DisableH2C,
    export.Export,
    onboarding.Onboarding,
    proxyauth.ProxyAuth,
    proxyserver.Proxyserver,
    script.ScriptLoader,
    dns_resolver.DnsResolver,
    next_layer.NextLayer,
    serverplayback.ServerPlayback,
    mapremote.MapRemote,
    maplocal.MapLocal,
    modifybody.ModifyBody,
    modifyheaders.ModifyHeaders,
    stickyauth.StickyAuth,
    stickycookie.StickyCookie,
    save.Save,
    savehar.SaveHar,
    tlsconfig.TlsConfig,
    upstream_auth.UpstreamAuth,
    update_alt_svc.UpdateAltSvc,
)


def _get_name(itm: Any) -> str:
    name = getattr(itm, "name", None)
    if isinstance(name, str):
        return name
    if isinstance(itm, type):
        return itm.__name__.lower()
    return itm.__class__.__name__.lower()


def _traverse(chain: Any):
    for a in chain:
        yield a
        if hasattr(a, "addons"):
            yield from _traverse(a.addons)


def _wrap_safe_load(addon: Any, ep_name: str) -> None:
    for a in _traverse([addon]):
        load_fn = getattr(a, "load", None)
        if callable(load_fn):
            orig_load = load_fn

            @functools.wraps(orig_load)
            def safe_load(loader: Any, *args: Any, **kwargs: Any) -> Any:
                try:
                    return orig_load(loader, *args, **kwargs)
                except Exception:
                    logger.error(
                        f"Addon '{_get_name(a)}' from entry point '{ep_name}' raised an exception in load():",
                        exc_info=True,
                    )

            with contextlib.suppress(AttributeError, TypeError):
                a.load = safe_load


def is_entrypoints_disabled() -> bool:
    for var in ("MITMPROXY_NO_ENTRYPOINTS", "MITMPROXY_NO_PLUGINS"):
        val = os.environ.get(var)
        if val is not None:
            return val.strip().lower() not in ("", "0", "false", "no")
    return False


def entrypoint_addons(reserved_names: set[str] | None = None) -> list[Any]:
    """
    Discover and load addons registered via Python entry points in group 'mitmproxy.addons'.

    Contracts & Isolation Policy:
    - Trust Model: Packages installed in the Python environment execute with ambient user privileges.
      Only trusted packages should be installed in the environment running mitmproxy.
    - Ordering Contract: Built-in addons load first in fixed order. Entry points load afterwards,
      sorted deterministically by entry point name (ep.name) in ascending order.
    - Idempotency Contract: This function is a pure factory; each invocation yields fresh instances.
    - Isolation Policy: Third-party entry points must never crash mitmproxy startup. Any entry point
      that fails during discovery, instantiation, factory invocation, name resolution, duplicate/collision
      checking, or load() hook execution is logged as an error and skipped atomically without leaving
      partial registration state.
    - Opt-Out Mechanism: Loading entry point addons can be disabled by setting either
      MITMPROXY_NO_ENTRYPOINTS=1 or MITMPROXY_NO_PLUGINS=1 in the environment.
    """
    if is_entrypoints_disabled():
        return []

    if reserved_names is None:
        reserved_names = {_get_name(cls) for cls in BUILTIN_ADDON_CLASSES}
    known_names = set(reserved_names)

    addons: list[Any] = []
    try:
        eps = sorted(
            importlib.metadata.entry_points(group="mitmproxy.addons"),
            key=lambda ep: ep.name,
        )
    except Exception:
        logger.error(
            "Failed to query entry points for group 'mitmproxy.addons'",
            exc_info=True,
        )
        return []

    for ep in eps:
        try:
            addon = ep.load()
            if isinstance(addon, type):
                addon = addon()
            elif callable(addon) and not isinstance(addon, types.ModuleType):
                is_zero_arg = False
                try:
                    sig = inspect.signature(addon)
                    is_zero_arg = not any(
                        p.default == inspect.Parameter.empty
                        and p.kind
                        in (
                            inspect.Parameter.POSITIONAL_ONLY,
                            inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        )
                        for p in sig.parameters.values()
                    )
                except (ValueError, TypeError):
                    is_zero_arg = False

                if is_zero_arg:
                    addon = addon()

            if isinstance(addon, (list, tuple)):
                items = list(addon)
            else:
                items = [addon]

            if len(items) == 1:
                if not getattr(items[0], "name", None):
                    with contextlib.suppress(AttributeError):
                        items[0].name = ep.name
            else:
                for idx, itm in enumerate(items):
                    if not getattr(itm, "name", None):
                        with contextlib.suppress(AttributeError):
                            itm.name = f"{ep.name}_{idx}"

            ep_names: list[str] = [_get_name(a) for a in _traverse(items)]

            if len(ep_names) != len(set(ep_names)):
                logger.error(
                    f"Entry point '{ep.name}' provides multiple addons with duplicate names: {ep_names}. "
                    "Skipping entry point."
                )
                continue

            conflicts = set(ep_names) & known_names
            if conflicts:
                logger.error(
                    f"Entry point '{ep.name}' conflicts with existing addon name(s): {sorted(conflicts)}. "
                    "Skipping entry point."
                )
                continue

            for itm in items:
                _wrap_safe_load(itm, ep.name)

            addons.extend(items)
            known_names.update(ep_names)
        except Exception:
            ep_val = getattr(ep, "value", ep.name)
            logger.error(
                f"Failed to load addon from entry point '{ep.name}': {ep_val}",
                exc_info=True,
            )

    return addons


def default_addons():
    builtins = [cls() for cls in BUILTIN_ADDON_CLASSES]
    reserved_names = {_get_name(a) for a in _traverse(builtins)}
    return [
        *builtins,
        *entrypoint_addons(reserved_names=reserved_names),
    ]
