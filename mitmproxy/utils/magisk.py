import hashlib
import os
from zipfile import ZipFile

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from mitmproxy import certs
from mitmproxy import ctx
from mitmproxy.options import CONF_BASENAME

# The following 3 variables are for including in the magisk module as text file
MODULE_PROP_TEXT = """id=mitmproxycert
name=MITMProxy cert
version=v1
versionCode=1
author=mitmproxy
description=Adds the mitmproxy certificate to the system store
template=3"""

CONFIG_SH_TEXT = """
MODID=mitmproxycert
AUTOMOUNT=true
PROPFILE=false
POSTFSDATA=false
LATESTARTSERVICE=false

print_modname() {
  ui_print "*******************************"
  ui_print "    MITMProxy cert installer   "
  ui_print "*******************************"
}

REPLACE="
"

set_permissions() {
  set_perm_recursive  $MODPATH  0  0  0755  0644
}
"""

UPDATE_BINARY_TEXT = """
#!/sbin/sh

#################
# Initialization
#################

umask 022

# echo before loading util_functions
ui_print() { echo "$1"; }

require_new_magisk() {
  ui_print "*******************************"
  ui_print " Please install Magisk v20.4+! "
  ui_print "*******************************"
  exit 1
}

OUTFD=$2
ZIPFILE=$3

mount /data 2>/dev/null
[ -f /data/adb/magisk/util_functions.sh ] || require_new_magisk
. /data/adb/magisk/util_functions.sh
[ $MAGISK_VER_CODE -lt 20400 ] && require_new_magisk

install_module
exit 0
"""


def get_ca_from_files() -> x509.Certificate:
    # Borrowed from tlsconfig
    certstore_path = os.path.expanduser(ctx.options.confdir)
    certstore = certs.CertStore.from_store(
        path=certstore_path,
        basename=CONF_BASENAME,
        key_size=ctx.options.key_size,
        passphrase=ctx.options.cert_passphrase.encode("utf8")
        if ctx.options.cert_passphrase
        else None,
    )
    return certstore.default_ca._cert


def subject_hash_old(ca: x509.Certificate) -> str:
    # Mimics the -subject_hash_old option of openssl used for android certificate names
    full_hash = hashlib.md5(ca.subject.public_bytes()).digest()
    sho = full_hash[0] | (full_hash[1] << 8) | (full_hash[2] << 16) | full_hash[3] << 24
    return hex(sho)[2:]


def write_magisk_module(path: str):
    # Makes a zip file that can be loaded by Magisk
    # Android certs are stored as DER files
    ca = get_ca_from_files()
    der_cert = ca.public_bytes(serialization.Encoding.DER)
    with ZipFile(path, "w") as zipp:
        # Main cert file, name is always the old subject hash with a '.0' added
        zipp.writestr(f"system/etc/security/cacerts/{subject_hash_old(ca)}.0", der_cert)
        zipp.writestr("module.prop", MODULE_PROP_TEXT)
        zipp.writestr("config.sh", CONFIG_SH_TEXT)
        zipp.writestr("META-INF/com/google/android/updater-script", "#MAGISK")
        zipp.writestr("META-INF/com/google/android/update-binary", UPDATE_BINARY_TEXT)
        zipp.writestr(
            "common/file_contexts_image", "/magisk(/.*)? u:object_r:system_file:s0"
        )
        zipp.writestr("common/post-fs-data.sh", "MODDIR=${0%/*}")
        zipp.writestr("common/service.sh", "MODDIR=${0%/*}")
        zipp.writestr("common/system.prop", "")
