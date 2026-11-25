"""Guards for the Windows InstallBuilder project used by release/build.py."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_XML = HERE.parents[1] / "release" / "installbuilder" / "mitmproxy.xml"


def _project_root() -> ET.Element:
    return ET.parse(PROJECT_XML).getroot()


def test_windows_arp_registry_prefix_is_version_independent():
    """
    InstallBuilder defaults windowsARPRegistryPrefix to "${fullName} ${version}",
    which creates a new ARP / winget ProductCode on every release (#6888).
    """
    prefix = _project_root().findtext("windowsARPRegistryPrefix")
    assert prefix is not None, "windowsARPRegistryPrefix must be set explicitly"
    assert "${project.version}" not in prefix
    assert "${product_version}" not in prefix
    assert prefix.strip() in {"${project.fullName}", "${product_fullname}", "mitmproxy"}


def test_upgrade_cleans_legacy_versioned_arp_keys():
    root = _project_root()
    ready = root.find("readyToInstallActionList")
    assert ready is not None, (
        "readyToInstallActionList required to clear legacy ARP keys"
    )

    deleted_keys = [
        action.findtext("key")
        for action in ready.iter("registryDelete")
        if action.findtext("key")
    ]
    assert any(
        "Uninstall\\${project.fullName} ${oldVersion}" in key for key in deleted_keys
    ), deleted_keys
    assert any(
        "ARPCache\\${project.fullName} ${oldVersion}" in key for key in deleted_keys
    ), deleted_keys

    # Cleanup must only run when reusing an existing installdir (unattended-safe).
    assert any(
        (rule.get("condition") or rule.findtext("condition")) == "exists"
        and (rule.get("path") or rule.findtext("path")) == "${installdir}"
        for rule in ready.iter("fileTest")
    ), "ARP cleanup must be gated on ${installdir} already existing"

    # registryFind+foreach is unsafe here: Uninstall key names contain spaces and
    # InstallBuilder foreach splits on spaces.
    assert not list(ready.iter("registryFind"))
    assert not list(ready.iter("foreach"))
