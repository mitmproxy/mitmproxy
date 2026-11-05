import contextlib
import datetime
import ipaddress
import logging
import os
import sys
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from typing import NewType
from typing import Optional
from typing import Union

import OpenSSL
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.types import CertificatePublicKeyTypes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import ExtendedKeyUsageOID
from cryptography.x509 import NameOID

from mitmproxy.coretypes import serializable

if sys.version_info < (3, 13):  # pragma: no cover
    from typing_extensions import deprecated
else:
    from warnings import deprecated

logger = logging.getLogger(__name__)

# Default expiry must not be too long: https://github.com/mitmproxy/mitmproxy/issues/815
# Note that expiry will be offset by `CERT_VALIDITY_OFFSET`, i.e. the cert will be
# backdated a bit to account for clients with incorrect clocks.
CA_EXPIRY = datetime.timedelta(days=10 * 365)
CERT_EXPIRY = datetime.timedelta(days=199)
CRL_EXPIRY = datetime.timedelta(days=7)

CERT_VALIDITY_OFFSET = datetime.timedelta(days=-2)

# Generated with "openssl dhparam". It's too slow to generate this on startup.
DEFAULT_DHPARAM = b"""
-----BEGIN DH PARAMETERS-----
MIICCAKCAgEAyT6LzpwVFS3gryIo29J5icvgxCnCebcdSe/NHMkD8dKJf8suFCg3
O2+dguLakSVif/t6dhImxInJk230HmfC8q93hdcg/j8rLGJYDKu3ik6H//BAHKIv
j5O9yjU3rXCfmVJQic2Nne39sg3CreAepEts2TvYHhVv3TEAzEqCtOuTjgDv0ntJ
Gwpj+BJBRQGG9NvprX1YGJ7WOFBP/hWU7d6tgvE6Xa7T/u9QIKpYHMIkcN/l3ZFB
chZEqVlyrcngtSXCROTPcDOQ6Q8QzhaBJS+Z6rcsd7X+haiQqvoFcmaJ08Ks6LQC
ZIL2EtYJw8V8z7C0igVEBIADZBI6OTbuuhDwRw//zU1uq52Oc48CIZlGxTYG/Evq
o9EWAXUYVzWkDSTeBH1r4z/qLPE2cnhtMxbFxuvK53jGB0emy2y1Ei6IhKshJ5qX
IB/aE7SSHyQ3MDHHkCmQJCsOd4Mo26YX61NZ+n501XjqpCBQ2+DfZCBh8Va2wDyv
A2Ryg9SUz8j0AXViRNMJgJrr446yro/FuJZwnQcO3WQnXeqSBnURqKjmqkeFP+d8
6mk2tqJaY507lRNqtGlLnj7f5RNoBFJDCLBNurVgfvq9TCVWKDIFD4vZRjCrnl6I
rD693XKIHUCWOjMh1if6omGXKHH40QuME2gNa50+YPn1iYDl88uDbbMCAQI=
-----END DH PARAMETERS-----
"""

# The compromised intermediate that --emudhra used before --emudhra-ca was
# introduced. Kept as the default so that existing invocations are
# unaffected.
DEFAULT_EMUDHRA_CA = "EM OV TLS CA - G3C"

# All compromised eMudhra intermediate CAs that can sign TLS server
# certificates, see https://emudhra.we-have-a-problem.com/.
#
# Each entry is a PEM bundle:
# 1. Private key for the intermediate.
# 2. Intermediate issued by emSign Root TLS CA - G3.
# 3. emSign Root TLS CA - G3 cross-signed by emSign ECC Root CA - G3.
# 4. Intermediate cross-signed by Sectigo's AAA Certificate Services.
#
# Path-building TLS stacks (Go, Rust, Java, macOS, Windows, browsers) consider all certificates in the chain
# and validate against any of the three roots (emSign ECC Root CA - G3, emSign Root TLS CA - G3, or
# AAA Certificate Services). OpenSSL does not backtrace across untrusted intermediates with the same
# Subject/SKI and only follows the first matching intermediate: --emudhra keeps the emSign-issued intermediate
# first (since Mozilla's root bundle used by Python/certifi, curl, Node.js, and Linux ca-certificates already
# removed AAA Certificate Services in 2025), while --emudhra-old moves the AAA-issued intermediate (#4) to the
# front for older OpenSSL trust stores.
#
# The two "EM OV CS CA" intermediates are deliberately excluded: their
# extendedKeyUsage is codeSigning only, so they cannot issue TLS server
# certificates.
EMUDHRA_CA_CHAINS: dict[str, bytes] = {
    "EM DV TLS CA - G3B": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJyhZANiAATnntnASpdz
xHNeUREdqFrCvV5kqzdLgOEsvCA47B5PDjuBL8mFnh5nr7BOL4vJf3SFumWqkR7o
pORbYtXMA9Vr5nizw4y03JN8okYOI4RTyJKTXSnUT5HhVga2PM7atGg=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDaDCCAu6gAwIBAgIQAKSu5njyM2K0wORgt3LyFDAKBggqhkjOPQQDAzBWMQsw
CQYDVQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRl
ZDEgMB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwHhcNMjUwNDMwMTU1
NDA4WhcNNDAwNDI4MTgzMDAwWjA/MQswCQYDVQQGEwJOTDETMBEGA1UECgwKZU11
ZGhyYSBCVjEbMBkGA1UEAwwSRU0gRFYgVExTIENBIC0gRzNCMHYwEAYHKoZIzj0C
AQYFK4EEACIDYgAE557ZwEqXc8RzXlERHahawr1eZKs3S4DhLLwgOOweTw47gS/J
hZ4eZ6+wTi+LyX90hbplqpEe6KTkW2LVzAPVa+Z4s8OMtNyTfKJGDiOEU8iSk10p
1E+R4VYGtjzO2rRoo4IBljCCAZIwHwYDVR0jBBgwFoAU4TqrIXzx401UrtRyt/2L
WUIgkFQwHQYDVR0OBBYEFOIeL+ccGTkOVUtiwSAkVzUkiiUUMB0GA1UdJQQWMBQG
CCsGAQUFBwMBBggrBgEFBQcDAjBdBgNVHSAEVjBUMDkGCysGAQQBg44hAQABMCow
KAYIKwYBBQUHAgEWHGh0dHA6Ly9yZXBvc2l0b3J5LmVtc2lnbi5jb20wDQYLKwYB
BAGDjiEBAmQwCAYGZ4EMAQIBMHUGCCsGAQUFBwEBBGkwZzAkBggrBgEFBQcwAYYY
aHR0cDovL29jc3AtYi5lbXNpZ24uY29tMD8GCCsGAQUFBzAChjNodHRwOi8vcmVw
b3NpdG9yeS5lbXNpZ24uY29tL2NlcnRzL0VNRFZUTFNDQUczQi5wN2MwNwYDVR0f
BDAwLjAsoCqgKIYmaHR0cDovL2NybC5lbXNpZ24uY29tLz9yb290dGxzY2FnMy5j
cmwwDgYDVR0PAQH/BAQDAgEGMBIGA1UdEwEB/wQIMAYBAf8CAQAwCgYIKoZIzj0E
AwMDaAAwZQIwLmsGXi6oFMJ2klkcEMXMug6gvxQWZWkewiDWVzQyl2L6z6DuQfPO
Ibh1grvdULDCAjEAxZvLlxUavG69J6wnSjC8XBbqNIQsJ6CE2QdNOe84Ptxb6VG8
gt2TlfJbHii+KNvK
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzjCCAragAwIBAgIRAKAk/fS6Zlx4XOSgIEg4WLcwDQYJKoZIhvcNAQELBQAw
ezELMAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNV
BAMMGEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczAeFw0yNTA1MTQwMDAwMDBaFw0y
ODEyMzEyMzU5NTlaMD8xCzAJBgNVBAYTAk5MMRMwEQYDVQQKDAplTXVkaHJhIEJW
MRswGQYDVQQDDBJFTSBEViBUTFMgQ0EgLSBHM0IwdjAQBgcqhkjOPQIBBgUrgQQA
IgNiAATnntnASpdzxHNeUREdqFrCvV5kqzdLgOEsvCA47B5PDjuBL8mFnh5nr7BO
L4vJf3SFumWqkR7opORbYtXMA9Vr5nizw4y03JN8okYOI4RTyJKTXSnUT5HhVga2
PM7atGijggE1MIIBMTAfBgNVHSMEGDAWgBSgEQojPpbxB+zirynvgqV/0DCktDAd
BgNVHQ4EFgQU4h4v5xwZOQ5VS2LBICRXNSSKJRQwDgYDVR0PAQH/BAQDAgEGMBIG
A1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMC
MDEGA1UdIAQqMCgwCAYGZ4EMAQIBMA0GCysGAQQBg44hAQABMA0GCysGAQQBg44h
AQJkMEMGA1UdHwQ8MDowOKA2oDSGMmh0dHA6Ly9jcmwuY29tb2RvY2EuY29tL0FB
QUNlcnRpZmljYXRlU2VydmljZXMuY3JsMDQGCCsGAQUFBwEBBCgwJjAkBggrBgEF
BQcwAYYYaHR0cDovL29jc3AuY29tb2RvY2EuY29tMA0GCSqGSIb3DQEBCwUAA4IB
AQBzQ1IoqpdotM6gFrR4Q3YrKifOLeaj5XXunldpVE/vZn2TxC2y0s8oYiLR5ICE
wqVXSB7N6BM1Mp+Nif7Jbhb2IswAfSR4Iik8+B0iRmi7lYoNlycCgHjmsjOmZaxM
QkPmjXAJbG5f4V41OsvJZmS7lI3r0IuvEDVX3GAZ13on6IImSs9ybNpHQ7NCqkMQ
7wH4uAO1dtpFycgJSdHaCOhHjrox2BTYGLdpUrYwY3EOAjlZ8UGgsxs7mG+xquMl
bN1LFURwfnkVMP3T/DBIZ/ys2+lNFyxK3FlArrV4/000uTnVB1lO8oGORYdXoT5V
GUyRCEIDhF5TBUuKF4E3kf1h
-----END CERTIFICATE-----
""",
    "EM DV TLS CA - G3C": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOahZANiAAQ6enhiyMRN
Mk3daQM6Z4LA7+7+QFXmihI/oDcbo72RlFFO4XKkM+NjDwK9GIA32eUUn5t325Si
gd+Yey/qiIt0vf6P2kwQme5soZVm/j7w5fawmlVszIulBWHfGypEHQE=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDaDCCAu6gAwIBAgIPWIsuPCu4zaE+GhIJJUMhMAoGCCqGSM49BAMDMFYxCzAJ
BgNVBAYTAklOMSUwIwYDVQQKDBxlTXVkaHJhIFRlY2hub2xvZ2llcyBMaW1pdGVk
MSAwHgYDVQQDDBdlbVNpZ24gUm9vdCBUTFMgQ0EgLSBHMzAeFw0yNTA0MzAxNTM1
MDlaFw00MDA0MjgxODMwMDBaMEAxCzAJBgNVBAYTAlVTMRQwEgYDVQQKDAtlTXVk
aHJhIEluYzEbMBkGA1UEAwwSRU0gRFYgVExTIENBIC0gRzNDMHYwEAYHKoZIzj0C
AQYFK4EEACIDYgAEOnp4YsjETTJN3WkDOmeCwO/u/kBV5ooSP6A3G6O9kZRRTuFy
pDPjYw8CvRiAN9nlFJ+bd9uUooHfmHsv6oiLdL3+j9pMEJnubKGVZv4+8OX2sJpV
bMyLpQVh3xsqRB0Bo4IBljCCAZIwHwYDVR0jBBgwFoAU4TqrIXzx401UrtRyt/2L
WUIgkFQwHQYDVR0OBBYEFK5+EFw8KZbBqEcnBVnx4D3U5QrzMB0GA1UdJQQWMBQG
CCsGAQUFBwMBBggrBgEFBQcDAjBdBgNVHSAEVjBUMDkGCysGAQQBg44hAQABMCow
KAYIKwYBBQUHAgEWHGh0dHA6Ly9yZXBvc2l0b3J5LmVtc2lnbi5jb20wDQYLKwYB
BAGDjiEBAmQwCAYGZ4EMAQIBMHUGCCsGAQUFBwEBBGkwZzAkBggrBgEFBQcwAYYY
aHR0cDovL29jc3AtYy5lbXNpZ24uY29tMD8GCCsGAQUFBzAChjNodHRwOi8vcmVw
b3NpdG9yeS5lbXNpZ24uY29tL2NlcnRzL0VNRFZUTFNDQUczQy5wN2MwNwYDVR0f
BDAwLjAsoCqgKIYmaHR0cDovL2NybC5lbXNpZ24uY29tLz9yb290dGxzY2FnMy5j
cmwwDgYDVR0PAQH/BAQDAgEGMBIGA1UdEwEB/wQIMAYBAf8CAQAwCgYIKoZIzj0E
AwMDaAAwZQIxAMEN2HWMocbuWdy1d33pH6JpMvP/V/DIS5PtZbv1Q7TXEbxrcyxg
yuddOJscYDJJlAIwB4sH1BpbScDzkdD4tJBSwrG/1Mx82vb8YaySehNuu1+1oXNd
AEKwaJ0mVzScy2+6
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzzCCAregAwIBAgIRAJHzR/Glt9OZYrleDuTimdEwDQYJKoZIhvcNAQELBQAw
ezELMAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNV
BAMMGEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczAeFw0yNTA1MTQwMDAwMDBaFw0y
ODEyMzEyMzU5NTlaMEAxCzAJBgNVBAYTAlVTMRQwEgYDVQQKDAtlTXVkaHJhIElu
YzEbMBkGA1UEAwwSRU0gRFYgVExTIENBIC0gRzNDMHYwEAYHKoZIzj0CAQYFK4EE
ACIDYgAEOnp4YsjETTJN3WkDOmeCwO/u/kBV5ooSP6A3G6O9kZRRTuFypDPjYw8C
vRiAN9nlFJ+bd9uUooHfmHsv6oiLdL3+j9pMEJnubKGVZv4+8OX2sJpVbMyLpQVh
3xsqRB0Bo4IBNTCCATEwHwYDVR0jBBgwFoAUoBEKIz6W8Qfs4q8p74Klf9AwpLQw
HQYDVR0OBBYEFK5+EFw8KZbBqEcnBVnx4D3U5QrzMA4GA1UdDwEB/wQEAwIBBjAS
BgNVHRMBAf8ECDAGAQH/AgEAMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcD
AjAxBgNVHSAEKjAoMAgGBmeBDAECATANBgsrBgEEAYOOIQEAATANBgsrBgEEAYOO
IQECZDBDBgNVHR8EPDA6MDigNqA0hjJodHRwOi8vY3JsLmNvbW9kb2NhLmNvbS9B
QUFDZXJ0aWZpY2F0ZVNlcnZpY2VzLmNybDA0BggrBgEFBQcBAQQoMCYwJAYIKwYB
BQUHMAGGGGh0dHA6Ly9vY3NwLmNvbW9kb2NhLmNvbTANBgkqhkiG9w0BAQsFAAOC
AQEAr7b6Mx11TIJgVzHt6EH5qGNWeiiqoMrp8E5/k8s+jvupx1n083pZ5XOzUzND
wEUe0W4C4FIGUHNQ4XDwqOw0yK42xqm2dvCKgsko2UvDlT0haZVtTCeWMQOe5J/J
ziaMfZwsZNfZ3aaI6XPtWDZtwY8AaNfyaeCpbtm5GcGnyNWk4jSNpbtpo6NjfXuP
CFOm3rTjJ4zytP7Tso6iMm0L01cYFOlTmoPv4515R2r3SPnKDtijoB/D/vgxzojv
DafgyG9afX8+laO9NbMMz4sqC1vZx3984i/sBNFiugm3Vvdq5OdJRjuGC1QILIs6
dg/K3i8VQqRpbfaM9kIlMzZ3dQ==
-----END CERTIFICATE-----
""",
    "EM EV TLS CA - G3B": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHOhZANiAAQl26haZNOX
2gsQUunqVG5Ie+/qnJ2daKDF6tz+73Wmm7XW/AH0K/vKbrQLzWTAdn42/9Bdl6gT
xaoMbJUw55z18IZkaPE4BkIKpchRhAseJSVA55DktlTDhS7WSvHoZX0=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDaDCCAu2gAwIBAgIQAMfEHv6S2CXwXq6EGkqCwTAKBggqhkjOPQQDAzBWMQsw
CQYDVQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRl
ZDEgMB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwHhcNMjUwNDMwMTYw
MzMxWhcNNDAwNDI4MTgzMDAwWjA/MQswCQYDVQQGEwJOTDETMBEGA1UECgwKZU11
ZGhyYSBCVjEbMBkGA1UEAwwSRU0gRVYgVExTIENBIC0gRzNCMHYwEAYHKoZIzj0C
AQYFK4EEACIDYgAEJduoWmTTl9oLEFLp6lRuSHvv6pydnWigxerc/u91ppu11vwB
9Cv7ym60C81kwHZ+Nv/QXZeoE8WqDGyVMOec9fCGZGjxOAZCCqXIUYQLHiUlQOeQ
5LZUw4Uu1krx6GV9o4IBlTCCAZEwHwYDVR0jBBgwFoAU4TqrIXzx401UrtRyt/2L
WUIgkFQwHQYDVR0OBBYEFD7cINmJRpiHe4c/2IFHslwV2EcGMB0GA1UdJQQWMBQG
CCsGAQUFBwMBBggrBgEFBQcDAjBcBgNVHSAEVTBTMDkGCysGAQQBg44hAQABMCow
KAYIKwYBBQUHAgEWHGh0dHA6Ly9yZXBvc2l0b3J5LmVtc2lnbi5jb20wDQYLKwYB
BAGDjiEBAngwBwYFZ4EMAQEwdQYIKwYBBQUHAQEEaTBnMCQGCCsGAQUFBzABhhho
dHRwOi8vb2NzcC1iLmVtc2lnbi5jb20wPwYIKwYBBQUHMAKGM2h0dHA6Ly9yZXBv
c2l0b3J5LmVtc2lnbi5jb20vY2VydHMvRU1FVlRMU0NBRzNCLnA3YzA3BgNVHR8E
MDAuMCygKqAohiZodHRwOi8vY3JsLmVtc2lnbi5jb20vP3Jvb3R0bHNjYWczLmNy
bDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIBADAKBggqhkjOPQQD
AwNpADBmAjEA9Jq999oaOUKhFwopw33iCmt0OHIn3gjT43GfuOHR/YckXdwoNdDA
lIEhz0NgRO3/AjEAvY/a3OMvktIZLYjn+WLKmp0QhrIMV+e6EpS7j4GVeOKouNp6
MN/P+ByGeiRMghzB
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzTCCArWgAwIBAgIRANj4aF5PK9nYJAKoWhwetzEwDQYJKoZIhvcNAQELBQAw
ezELMAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNV
BAMMGEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczAeFw0yNTA1MTQwMDAwMDBaFw0y
ODEyMzEyMzU5NTlaMD8xCzAJBgNVBAYTAk5MMRMwEQYDVQQKDAplTXVkaHJhIEJW
MRswGQYDVQQDDBJFTSBFViBUTFMgQ0EgLSBHM0IwdjAQBgcqhkjOPQIBBgUrgQQA
IgNiAAQl26haZNOX2gsQUunqVG5Ie+/qnJ2daKDF6tz+73Wmm7XW/AH0K/vKbrQL
zWTAdn42/9Bdl6gTxaoMbJUw55z18IZkaPE4BkIKpchRhAseJSVA55DktlTDhS7W
SvHoZX2jggE0MIIBMDAfBgNVHSMEGDAWgBSgEQojPpbxB+zirynvgqV/0DCktDAd
BgNVHQ4EFgQUPtwg2YlGmId7hz/YgUeyXBXYRwYwDgYDVR0PAQH/BAQDAgEGMBIG
A1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMC
MDAGA1UdIAQpMCcwBwYFZ4EMAQEwDQYLKwYBBAGDjiEBAAEwDQYLKwYBBAGDjiEB
AngwQwYDVR0fBDwwOjA4oDagNIYyaHR0cDovL2NybC5jb21vZG9jYS5jb20vQUFB
Q2VydGlmaWNhdGVTZXJ2aWNlcy5jcmwwNAYIKwYBBQUHAQEEKDAmMCQGCCsGAQUF
BzABhhhodHRwOi8vb2NzcC5jb21vZG9jYS5jb20wDQYJKoZIhvcNAQELBQADggEB
AJNFuAFW9Gnw/8+kCO4KIlZdnM1Sh2u+8cK0EYAHhXpb5FlGvYkcARigo5oS7VoM
7FOYlTueV6yICZKNAYawZPJPhNCGK+rp3cQBEz6d0n8OZEYZov9lb3ll8ORgSDuf
FVIW6Gagg/UnOamLBTOR8eD5V73SCme/B2cHUDw+m5E8cc+0Ujzz3Cn3ex5JrhXk
2T3s8PoVzEmhTgGboFfcWO1EYhPPrYwdxPYRQIXAXUXhLEOVNL9ASbZJLFI8E1IM
m7NwxVN2s38jWpaCUaaF0tg7hfiy7oe13rzJfHsdqldJVTTUTPWVx8TC4ju0VLet
bAlwhwFT6AP8uIVMGUHNw24=
-----END CERTIFICATE-----
""",
    "EM EV TLS CA - G3C": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADihZANiAAQtVugppvuC
xkpGl9lgr5UekGeukfkm00MG2kioqut4abamfm0nQm4EQqoDs24ZiN/2NlFO4c8H
9bpLP/KgZkWufTHVhmrTGqPSRusLMXfumct1ZsUWznSAimaPkfDEf8o=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDaDCCAu6gAwIBAgIQAIAJkopkEHYBrwX6LxnxCTAKBggqhkjOPQQDAzBWMQsw
CQYDVQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRl
ZDEgMB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwHhcNMjUwNDMwMTUz
OTMxWhcNNDAwNDI4MTgzMDAwWjBAMQswCQYDVQQGEwJVUzEUMBIGA1UECgwLZU11
ZGhyYSBJbmMxGzAZBgNVBAMMEkVNIEVWIFRMUyBDQSAtIEczQzB2MBAGByqGSM49
AgEGBSuBBAAiA2IABC1W6Cmm+4LGSkaX2WCvlR6QZ66R+SbTQwbaSKiq63hptqZ+
bSdCbgRCqgOzbhmI3/Y2UU7hzwf1uks/8qBmRa59MdWGatMao9JG6wsxd+6Zy3Vm
xRbOdICKZo+R8MR/yqOCAZUwggGRMB8GA1UdIwQYMBaAFOE6qyF88eNNVK7Ucrf9
i1lCIJBUMB0GA1UdDgQWBBSmJV6AqU2385Z8G8eR35K87kvrXzAdBgNVHSUEFjAU
BggrBgEFBQcDAQYIKwYBBQUHAwIwXAYDVR0gBFUwUzA5BgsrBgEEAYOOIQEAATAq
MCgGCCsGAQUFBwIBFhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMA0GCysG
AQQBg44hAQJ4MAcGBWeBDAEBMHUGCCsGAQUFBwEBBGkwZzAkBggrBgEFBQcwAYYY
aHR0cDovL29jc3AtYy5lbXNpZ24uY29tMD8GCCsGAQUFBzAChjNodHRwOi8vcmVw
b3NpdG9yeS5lbXNpZ24uY29tL2NlcnRzL0VNRVZUTFNDQUczQy5wN2MwNwYDVR0f
BDAwLjAsoCqgKIYmaHR0cDovL2NybC5lbXNpZ24uY29tLz9yb290dGxzY2FnMy5j
cmwwDgYDVR0PAQH/BAQDAgEGMBIGA1UdEwEB/wQIMAYBAf8CAQAwCgYIKoZIzj0E
AwMDaAAwZQIwBy1wTnzH4lXDTy2PD91ysLjvnlVN3JbJmc1BIMEU8TOLkYVHibMc
9HeyonikFSfmAjEA6uE3QRxlrZTz/1/lXPTEMUhoauAtycagtlNFp79kjhvNa2/f
Aal1GNxsOutLnr0Y
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzTCCArWgAwIBAgIQBfB4dS3s56G7hZXTAxZxcTANBgkqhkiG9w0BAQsFADB7
MQswCQYDVQQGEwJHQjEbMBkGA1UECAwSR3JlYXRlciBNYW5jaGVzdGVyMRAwDgYD
VQQHDAdTYWxmb3JkMRowGAYDVQQKDBFDb21vZG8gQ0EgTGltaXRlZDEhMB8GA1UE
AwwYQUFBIENlcnRpZmljYXRlIFNlcnZpY2VzMB4XDTI1MDUxNDAwMDAwMFoXDTI4
MTIzMTIzNTk1OVowQDELMAkGA1UEBhMCVVMxFDASBgNVBAoMC2VNdWRocmEgSW5j
MRswGQYDVQQDDBJFTSBFViBUTFMgQ0EgLSBHM0MwdjAQBgcqhkjOPQIBBgUrgQQA
IgNiAAQtVugppvuCxkpGl9lgr5UekGeukfkm00MG2kioqut4abamfm0nQm4EQqoD
s24ZiN/2NlFO4c8H9bpLP/KgZkWufTHVhmrTGqPSRusLMXfumct1ZsUWznSAimaP
kfDEf8qjggE0MIIBMDAfBgNVHSMEGDAWgBSgEQojPpbxB+zirynvgqV/0DCktDAd
BgNVHQ4EFgQUpiVegKlNt/OWfBvHkd+SvO5L618wDgYDVR0PAQH/BAQDAgEGMBIG
A1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMC
MDAGA1UdIAQpMCcwBwYFZ4EMAQEwDQYLKwYBBAGDjiEBAAEwDQYLKwYBBAGDjiEB
AngwQwYDVR0fBDwwOjA4oDagNIYyaHR0cDovL2NybC5jb21vZG9jYS5jb20vQUFB
Q2VydGlmaWNhdGVTZXJ2aWNlcy5jcmwwNAYIKwYBBQUHAQEEKDAmMCQGCCsGAQUF
BzABhhhodHRwOi8vb2NzcC5jb21vZG9jYS5jb20wDQYJKoZIhvcNAQELBQADggEB
AIFfHiaMSjnrdZygRYV4ekRBmG7ybcFk4hGQWMMyMFi0cAEk2+dGfz5bl8IaIbLq
z+uVJzhOgVEX7WqIfgbWfFsfPYHYjPHBmy7SlZ3BwA86IQ6qF/etpX2/qL9A5yRN
N3nVowUpaqV6H3aCpkAh3wR2ZNkvAbLDvPz3J0l+sEWjWv+ZISOV4R+hXDTdPXV0
1lKxnbwqEsdo/sE2QkCDKwFrZh/0uKjWspydJj+jSaDLTrGNx50Dgmn7VEcD1ZI5
FXjknVUiO25YlmS1dtVZSBbyUKSjlrP/yDwPcZunoAsmCAAtCKsFLviLaymzvsKI
eSSDGxpSySp2VCxompGDk8g=
-----END CERTIFICATE-----
""",
    "EM OV TLS CA - G3B": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJuhZANiAARziXqg6zz9
yosSQC/68KvE4SErr43ud4rJ7i1tuD+sKAxeBWOK56Ks1xwyKo42HN659pxDArnd
jXPRzGyqsswK7k4hbOl53VGKSvS2JuVoTN1lgDftDIVOTMEvTPhkbQ0=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDZjCCAu2gAwIBAgIPbK2jZ/scEACIEg6iAtVoMAoGCCqGSM49BAMDMFYxCzAJ
BgNVBAYTAklOMSUwIwYDVQQKDBxlTXVkaHJhIFRlY2hub2xvZ2llcyBMaW1pdGVk
MSAwHgYDVQQDDBdlbVNpZ24gUm9vdCBUTFMgQ0EgLSBHMzAeFw0yNTA0MzAxNjAw
MTJaFw00MDA0MjgxODMwMDBaMD8xCzAJBgNVBAYTAk5MMRMwEQYDVQQKDAplTXVk
aHJhIEJWMRswGQYDVQQDDBJFTSBPViBUTFMgQ0EgLSBHM0IwdjAQBgcqhkjOPQIB
BgUrgQQAIgNiAARziXqg6zz9yosSQC/68KvE4SErr43ud4rJ7i1tuD+sKAxeBWOK
56Ks1xwyKo42HN659pxDArndjXPRzGyqsswK7k4hbOl53VGKSvS2JuVoTN1lgDft
DIVOTMEvTPhkbQ2jggGWMIIBkjAfBgNVHSMEGDAWgBThOqshfPHjTVSu1HK3/YtZ
QiCQVDAdBgNVHQ4EFgQUm9hlUa/n5yw3rQjuaRnZvzeErgowHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMF0GA1UdIARWMFQwOQYLKwYBBAGDjiEBAAEwKjAo
BggrBgEFBQcCARYcaHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbTANBgsrBgEE
AYOOIQECbjAIBgZngQwBAgIwdQYIKwYBBQUHAQEEaTBnMCQGCCsGAQUFBzABhhho
dHRwOi8vb2NzcC1iLmVtc2lnbi5jb20wPwYIKwYBBQUHMAKGM2h0dHA6Ly9yZXBv
c2l0b3J5LmVtc2lnbi5jb20vY2VydHMvRU1PVlRMU0NBRzNCLnA3YzA3BgNVHR8E
MDAuMCygKqAohiZodHRwOi8vY3JsLmVtc2lnbi5jb20vP3Jvb3R0bHNjYWczLmNy
bDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIBADAKBggqhkjOPQQD
AwNnADBkAjBAk+5BizdJhrED3wb7F2Gm7bWI60dlNd075nghT2TrR4NWKZtJZcbc
28xxIY/NONICMF6mPdsjosaqmvEMWqKcBh4vsIvXSKnQj5o8zrFB4oKS+accjYTe
8Dz3bQjauvy9uw==
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzjCCAragAwIBAgIRAOlCI73pL5FOWrmsq/2sNxAwDQYJKoZIhvcNAQELBQAw
ezELMAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNV
BAMMGEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczAeFw0yNTA1MTQwMDAwMDBaFw0y
ODEyMzEyMzU5NTlaMD8xCzAJBgNVBAYTAk5MMRMwEQYDVQQKDAplTXVkaHJhIEJW
MRswGQYDVQQDDBJFTSBPViBUTFMgQ0EgLSBHM0IwdjAQBgcqhkjOPQIBBgUrgQQA
IgNiAARziXqg6zz9yosSQC/68KvE4SErr43ud4rJ7i1tuD+sKAxeBWOK56Ks1xwy
Ko42HN659pxDArndjXPRzGyqsswK7k4hbOl53VGKSvS2JuVoTN1lgDftDIVOTMEv
TPhkbQ2jggE1MIIBMTAfBgNVHSMEGDAWgBSgEQojPpbxB+zirynvgqV/0DCktDAd
BgNVHQ4EFgQUm9hlUa/n5yw3rQjuaRnZvzeErgowDgYDVR0PAQH/BAQDAgEGMBIG
A1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYIKwYBBQUHAwEGCCsGAQUFBwMC
MDEGA1UdIAQqMCgwCAYGZ4EMAQICMA0GCysGAQQBg44hAQABMA0GCysGAQQBg44h
AQJuMEMGA1UdHwQ8MDowOKA2oDSGMmh0dHA6Ly9jcmwuY29tb2RvY2EuY29tL0FB
QUNlcnRpZmljYXRlU2VydmljZXMuY3JsMDQGCCsGAQUFBwEBBCgwJjAkBggrBgEF
BQcwAYYYaHR0cDovL29jc3AuY29tb2RvY2EuY29tMA0GCSqGSIb3DQEBCwUAA4IB
AQALRoOSvkzRa+tN5Rje9W5GiXd/qsicd9N6Gnh0SWC7VyWH+HycIqAnFCMYZznj
CeGusomFYHE42SHWr85JDIbgzy6y3dO4i9n9w0Bx7yrXWBbDzFS8VgA3+EY4Cg7y
mtoC3RPOJVtaXXPZ+68X804g1Mj+3vCSHj2lNPVgco0OzSIOJ/KMg1R9MLBkiKzb
bERAGZHejY0HBhYd76IINZN8z6bBNah2UdFYxsOisLynPQUkol6gRLum024/FzVl
CCDfnUusrkr+mAfPAvD/Vb8bhpA7jYtepuU+2mIdShj5lLlvAwZphn+ypWycuo2x
0k9mldz2dqI9nhCiY+TTIOOR
-----END CERTIFICATE-----
""",
    "EM OV TLS CA - G3C": b"""
-----BEGIN PRIVATE KEY-----
MIG2AgEAMBAGByqGSM49AgEGBSuBBAAiBIGeMIGbAgEBBDAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAShZANiAAQTglHNUqyS
mMHIqtl3Mh3rl+cJvQtMoKylXcitUdz8nRWJoVl+OlEg4e/WMcY+GDXKyuKYaaYu
FjHoooGBq1ZhbcRdkYq8CfOrDmPPeSqk3O1zh743u6VpVJ8cArJw7Wc=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDaDCCAu6gAwIBAgIPKWkmwiejoVJjkrGUgqUEMAoGCCqGSM49BAMDMFYxCzAJ
BgNVBAYTAklOMSUwIwYDVQQKDBxlTXVkaHJhIFRlY2hub2xvZ2llcyBMaW1pdGVk
MSAwHgYDVQQDDBdlbVNpZ24gUm9vdCBUTFMgQ0EgLSBHMzAeFw0yNTA0MzAxNTM3
NDFaFw00MDA0MjgxODMwMDBaMEAxCzAJBgNVBAYTAlVTMRQwEgYDVQQKDAtlTXVk
aHJhIEluYzEbMBkGA1UEAwwSRU0gT1YgVExTIENBIC0gRzNDMHYwEAYHKoZIzj0C
AQYFK4EEACIDYgAEE4JRzVKskpjByKrZdzId65fnCb0LTKCspV3IrVHc/J0ViaFZ
fjpRIOHv1jHGPhg1ysrimGmmLhYx6KKBgatWYW3EXZGKvAnzqw5jz3kqpNztc4e+
N7ulaVSfHAKycO1no4IBljCCAZIwHwYDVR0jBBgwFoAU4TqrIXzx401UrtRyt/2L
WUIgkFQwHQYDVR0OBBYEFDTq6gzryQra+dDF4u2beMmHnhtsMB0GA1UdJQQWMBQG
CCsGAQUFBwMBBggrBgEFBQcDAjBdBgNVHSAEVjBUMDkGCysGAQQBg44hAQABMCow
KAYIKwYBBQUHAgEWHGh0dHA6Ly9yZXBvc2l0b3J5LmVtc2lnbi5jb20wDQYLKwYB
BAGDjiEBAm4wCAYGZ4EMAQICMHUGCCsGAQUFBwEBBGkwZzAkBggrBgEFBQcwAYYY
aHR0cDovL29jc3AtYy5lbXNpZ24uY29tMD8GCCsGAQUFBzAChjNodHRwOi8vcmVw
b3NpdG9yeS5lbXNpZ24uY29tL2NlcnRzL0VNT1ZUTFNDQUczQy5wN2MwNwYDVR0f
BDAwLjAsoCqgKIYmaHR0cDovL2NybC5lbXNpZ24uY29tLz9yb290dGxzY2FnMy5j
cmwwDgYDVR0PAQH/BAQDAgEGMBIGA1UdEwEB/wQIMAYBAf8CAQAwCgYIKoZIzj0E
AwMDaAAwZQIxAMSZt2xsPeumRdeSMSQ3CbzIZeQ/q7GDCWfeE1Pq+mhgA6gRM44c
NVF3xJ+wsxJk+wIwFJbaDMokD8Ei6eNOiA8yUMYvfzQyngmrhZQMdPCK1SewrR79
4rSb9vGqxZzelQth
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDdDCCAvmgAwIBAgIQAJYaPvsTWVdu0EAFtGhKWzAKBggqhkjOPQQDAzBrMQsw
CQYDVQQGEwJJTjETMBEGA1UECxMKZW1TaWduIFBLSTElMCMGA1UEChMcZU11ZGhy
YSBUZWNobm9sb2dpZXMgTGltaXRlZDEgMB4GA1UEAxMXZW1TaWduIEVDQyBSb290
IENBIC0gRzMwHhcNMjQwNzExMTU0MzM2WhcNMzkwNzA5MTgzMDAwWjBWMQswCQYD
VQQGEwJJTjElMCMGA1UECgwcZU11ZGhyYSBUZWNobm9sb2dpZXMgTGltaXRlZDEg
MB4GA1UEAwwXZW1TaWduIFJvb3QgVExTIENBIC0gRzMwdjAQBgcqhkjOPQIBBgUr
gQQAIgNiAARfD9w/q1cWxL6D9bMGH6CQ4u+gAV6GN9s+PwQx9Bl4hC+0iU8QOk8m
WO/RwXQy10DCSxT8vSIJClHKp+Ao4qJKdYeV0SwZ7LMQziyLfxIUOY6Grja/sQFw
LKYf8EdDXAyjggF1MIIBcTAfBgNVHSMEGDAWgBR8XQKEE9TMipuBzhccLikenEhj
QjAdBgNVHQ4EFgQU4TqrIXzx401UrtRyt/2LWUIgkFQwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMD0GA1UdIAQ2MDQwMgYEVR0gADAqMCgGCCsGAQUFBwIB
FhxodHRwOi8vcmVwb3NpdG9yeS5lbXNpZ24uY29tMHgGCCsGAQUFBwEBBGwwajAi
BggrBgEFBQcwAYYWaHR0cDovL29jc3AuZW1zaWduLmNvbTBEBggrBgEFBQcwAoY4
aHR0cDovL3JlcG9zaXRvcnkuZW1zaWduLmNvbS9jZXJ0cy9lbVNpZ25FQ0NSb290
Q0FHMy5jcnQwMwYDVR0fBCwwKjAooCagJIYiaHR0cDovL2NybC5lbXNpZ24uY29t
P1Jvb3RDQUczLmNybDAOBgNVHQ8BAf8EBAMCAQYwEgYDVR0TAQH/BAgwBgEB/wIB
ATAKBggqhkjOPQQDAwNpADBmAjEAt9CIpRGp46QHQYDUBnLKw+vvK0/h9vmilEAg
TroUl/anH4x2rXHqiCtBTBfgKDegAjEA8WpG1LTZdAIL0FSYqxXeREaeTSxEofM0
1jJH3jGvCXC79LU9UPJ2o3TU+UIj2gMV
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIDzzCCAregAwIBAgIRAI1aSBGTnvRH13ERzdmEmukwDQYJKoZIhvcNAQELBQAw
ezELMAkGA1UEBhMCR0IxGzAZBgNVBAgMEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4G
A1UEBwwHU2FsZm9yZDEaMBgGA1UECgwRQ29tb2RvIENBIExpbWl0ZWQxITAfBgNV
BAMMGEFBQSBDZXJ0aWZpY2F0ZSBTZXJ2aWNlczAeFw0yNTA1MTQwMDAwMDBaFw0y
ODEyMzEyMzU5NTlaMEAxCzAJBgNVBAYTAlVTMRQwEgYDVQQKDAtlTXVkaHJhIElu
YzEbMBkGA1UEAwwSRU0gT1YgVExTIENBIC0gRzNDMHYwEAYHKoZIzj0CAQYFK4EE
ACIDYgAEE4JRzVKskpjByKrZdzId65fnCb0LTKCspV3IrVHc/J0ViaFZfjpRIOHv
1jHGPhg1ysrimGmmLhYx6KKBgatWYW3EXZGKvAnzqw5jz3kqpNztc4e+N7ulaVSf
HAKycO1no4IBNTCCATEwHwYDVR0jBBgwFoAUoBEKIz6W8Qfs4q8p74Klf9AwpLQw
HQYDVR0OBBYEFDTq6gzryQra+dDF4u2beMmHnhtsMA4GA1UdDwEB/wQEAwIBBjAS
BgNVHRMBAf8ECDAGAQH/AgEAMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcD
AjAxBgNVHSAEKjAoMAgGBmeBDAECAjANBgsrBgEEAYOOIQEAATANBgsrBgEEAYOO
IQECbjBDBgNVHR8EPDA6MDigNqA0hjJodHRwOi8vY3JsLmNvbW9kb2NhLmNvbS9B
QUFDZXJ0aWZpY2F0ZVNlcnZpY2VzLmNybDA0BggrBgEFBQcBAQQoMCYwJAYIKwYB
BQUHMAGGGGh0dHA6Ly9vY3NwLmNvbW9kb2NhLmNvbTANBgkqhkiG9w0BAQsFAAOC
AQEAHlbhZpjhkPEAQVhPHRtBDaHqiisVD20pQ1TUeSx3l62Qe7NQ0b7vWQy7DN0i
KOu7BGpP5EnIjvXbz9FhpfPJ4FhKEt3tQ51rqXz2oD8vRaryvExWPobDUz3j7HN6
OzBsVMIe3PD7AAkpky0x8zMSi/ep5R9OMzybmNptbtppyuB5ytgq+h7lQdRIP+CQ
TaJX3qTgfMqzntYre5GljmEB5hU2/rSn8zoSU2APkJidlZFpghtgbD4I2VRHZvCw
FFr/SrFM9pwrgbJNZ1MtyTSVgI5NlNb0aMfLR+/r6jJt3ROeY2yh2QQ2dx+Yqgdb
uL5ChFWOQU+ErSDnUq7yr+pjBQ==
-----END CERTIFICATE-----
""",
}

# Backwards-compatible alias for the CA that --emudhra used before
# --emudhra-ca was introduced. Kept so that downstream code importing
# EMUDHRA_CHAIN_PEM keeps working.
EMUDHRA_CHAIN_PEM = EMUDHRA_CA_CHAINS[DEFAULT_EMUDHRA_CA]


class Cert(serializable.Serializable):
    """Representation of a (TLS) certificate."""

    _cert: x509.Certificate

    def __init__(self, cert: x509.Certificate):
        assert isinstance(cert, x509.Certificate)
        self._cert = cert

    def __eq__(self, other):
        return self.fingerprint() == other.fingerprint()

    def __repr__(self):
        altnames = [str(x.value) for x in self.altnames]
        return f"<Cert(cn={self.cn!r}, altnames={altnames!r})>"

    def __hash__(self):
        return self._cert.__hash__()

    @classmethod
    def from_state(cls, state):
        return cls.from_pem(state)

    def get_state(self):
        return self.to_pem()

    def set_state(self, state):
        self._cert = x509.load_pem_x509_certificate(state)

    @classmethod
    def from_pem(cls, data: bytes) -> "Cert":
        cert = x509.load_pem_x509_certificate(data)  # type: ignore
        return cls(cert)

    def to_pem(self) -> bytes:
        return self._cert.public_bytes(serialization.Encoding.PEM)

    @classmethod
    def from_pyopenssl(self, x509: OpenSSL.crypto.X509) -> "Cert":
        return Cert(x509.to_cryptography())

    @deprecated("Use `to_cryptography` instead.")
    def to_pyopenssl(self) -> OpenSSL.crypto.X509:  # pragma: no cover
        return OpenSSL.crypto.X509.from_cryptography(self._cert)

    def to_cryptography(self) -> x509.Certificate:
        return self._cert

    def public_key(self) -> CertificatePublicKeyTypes:
        return self._cert.public_key()

    def fingerprint(self) -> bytes:
        return self._cert.fingerprint(hashes.SHA256())

    @property
    def issuer(self) -> list[tuple[str, str]]:
        return _name_to_keyval(self._cert.issuer)

    @property
    def notbefore(self) -> datetime.datetime:
        try:
            # type definitions haven't caught up with new API yet.
            return self._cert.not_valid_before_utc  # type: ignore
        except AttributeError:  # pragma: no cover
            # cryptography < 42.0
            return self._cert.not_valid_before.replace(tzinfo=datetime.UTC)

    @property
    def notafter(self) -> datetime.datetime:
        try:
            return self._cert.not_valid_after_utc  # type: ignore
        except AttributeError:  # pragma: no cover
            return self._cert.not_valid_after.replace(tzinfo=datetime.UTC)

    def has_expired(self) -> bool:
        if sys.version_info < (3, 11):  # pragma: no cover
            return datetime.datetime.now(datetime.UTC) > self.notafter
        return datetime.datetime.now(datetime.UTC) > self.notafter

    @property
    def subject(self) -> list[tuple[str, str]]:
        return _name_to_keyval(self._cert.subject)

    @property
    def serial(self) -> int:
        return self._cert.serial_number

    @property
    def is_ca(self) -> bool:
        constraints: x509.BasicConstraints
        try:
            constraints = self._cert.extensions.get_extension_for_class(
                x509.BasicConstraints
            ).value
            return constraints.ca
        except x509.ExtensionNotFound:
            return False

    @property
    def keyinfo(self) -> tuple[str, int]:
        public_key = self._cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            return "RSA", public_key.key_size
        if isinstance(public_key, dsa.DSAPublicKey):
            return "DSA", public_key.key_size
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            return f"EC ({public_key.curve.name})", public_key.key_size
        return (
            public_key.__class__.__name__.replace("PublicKey", "").replace("_", ""),
            getattr(public_key, "key_size", -1),
        )  # pragma: no cover

    @property
    def cn(self) -> str | None:
        attrs = self._cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        if attrs:
            return cast(str, attrs[0].value)
        return None

    @property
    def organization(self) -> str | None:
        attrs = self._cert.subject.get_attributes_for_oid(
            x509.NameOID.ORGANIZATION_NAME
        )
        if attrs:
            return cast(str, attrs[0].value)
        return None

    @property
    def altnames(self) -> x509.GeneralNames:
        """
        Get all SubjectAlternativeName DNS altnames.
        """
        try:
            sans = self._cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
        except x509.ExtensionNotFound:
            return x509.GeneralNames([])
        else:
            return x509.GeneralNames(sans)

    @property
    def crl_distribution_points(self) -> list[str]:
        try:
            ext = self._cert.extensions.get_extension_for_class(
                x509.CRLDistributionPoints
            ).value
        except x509.ExtensionNotFound:
            return []
        else:
            return [
                dist_point.full_name[0].value
                for dist_point in ext
                if dist_point.full_name
                and isinstance(dist_point.full_name[0], x509.UniformResourceIdentifier)
            ]


def _name_to_keyval(name: x509.Name) -> list[tuple[str, str]]:
    parts = []
    for attr in name:
        k = attr.rfc4514_string().partition("=")[0]
        v = cast(str, attr.value)
        parts.append((k, v))
    return parts


def create_ca(
    organization: str,
    cn: str,
    key_size: int,
) -> tuple[rsa.RSAPrivateKeyWithSerialization, x509.Certificate]:
    now = datetime.datetime.now()

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )  # type: ignore
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        ]
    )
    builder = x509.CertificateBuilder()
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.subject_name(name)
    builder = builder.not_valid_before(now + CERT_VALIDITY_OFFSET)
    builder = builder.not_valid_after(now + CERT_VALIDITY_OFFSET + CA_EXPIRY)
    builder = builder.issuer_name(name)
    builder = builder.public_key(private_key.public_key())
    builder = builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True
    )
    builder = builder.add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
    )
    builder = builder.add_extension(
        x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False,
    )
    cert = builder.sign(private_key=private_key, algorithm=hashes.SHA256())  # type: ignore
    return private_key, cert


def _fix_legacy_sans(sans: Iterable[x509.GeneralName] | list[str]) -> x509.GeneralNames:
    """
    SANs used to be a list of strings in mitmproxy 10.1 and below, but now they're a list of GeneralNames.
    This function converts the old format to the new one.
    """
    if isinstance(sans, x509.GeneralNames):
        return sans
    elif (
        isinstance(sans, list) and len(sans) > 0 and isinstance(sans[0], str)
    ):  # pragma: no cover
        warnings.warn(
            "Passing SANs as a list of strings is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )

        ss: list[x509.GeneralName] = []
        for x in cast(list[str], sans):
            try:
                ip = ipaddress.ip_address(x)
            except ValueError:
                x = x.encode("idna").decode()
                ss.append(x509.DNSName(x))
            else:
                ss.append(x509.IPAddress(ip))
        return x509.GeneralNames(ss)
    else:
        return x509.GeneralNames(cast(Iterable[x509.GeneralName], sans))


def dummy_cert(
    privkey: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey,
    cacert: x509.Certificate,
    commonname: str | None,
    sans: Iterable[x509.GeneralName],
    organization: str | None = None,
    crl_url: str | None = None,
) -> Cert:
    """
    Generates a dummy certificate.

    privkey: CA private key
    cacert: CA certificate
    commonname: Common name for the generated certificate.
    sans: A list of Subject Alternate Names.
    organization: Organization name for the generated certificate.
    crl_url: URL of CRL distribution point

    Returns cert if operation succeeded, None if not.
    """
    builder = x509.CertificateBuilder()
    builder = builder.issuer_name(cacert.subject)
    builder = builder.add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
    )
    builder = builder.public_key(cacert.public_key())

    now = datetime.datetime.now()
    builder = builder.not_valid_before(now + CERT_VALIDITY_OFFSET)
    builder = builder.not_valid_after(now + CERT_VALIDITY_OFFSET + CERT_EXPIRY)

    subject = []
    is_valid_commonname = commonname is not None and len(commonname) < 64
    if is_valid_commonname:
        assert commonname is not None
        subject.append(x509.NameAttribute(NameOID.COMMON_NAME, commonname))
    if organization is not None:
        assert organization is not None
        subject.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
    builder = builder.subject_name(x509.Name(subject))
    builder = builder.serial_number(x509.random_serial_number())

    sans = _fix_legacy_sans(sans)
    if sans:
        # RFC 5280 §4.2.1.6: subjectAltName is critical if subject is empty.
        builder = builder.add_extension(
            x509.SubjectAlternativeName(sans),
            critical=not is_valid_commonname,
        )

    # https://datatracker.ietf.org/doc/html/rfc5280#section-4.2.1.1
    # Per RFC 5280 §4.2.1.2, the AKI's keyIdentifier in a child certificate
    # MUST be byte-equal to the issuer's stored SubjectKeyIdentifier. If we
    # recompute it from the public key with `from_issuer_public_key()`, we
    # always derive a SHA-1 digest, which mismatches whenever the issuer's
    # SKI was generated by a different method (RFC 7093 truncated
    # SHA-256/384/512, hardware-rooted CAs, or any custom value). This
    # mismatch is rejected by strict TLS chain builders (`X509_V_FLAG_X509_STRICT`,
    # Python `ssl`, Go `crypto/x509`) with "authority and subject key
    # identifier mismatch". Most notably, cert-manager >=1.18 / Go >=1.25
    # default to truncated SHA-256 SKIs for FIPS 140-3 compliance.
    try:
        issuer_ski = cacert.extensions.get_extension_for_class(
            x509.SubjectKeyIdentifier
        ).value
        aki = x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(issuer_ski)
    except x509.ExtensionNotFound:
        # Fall back when the issuer cert has no SKI extension at all (legacy
        # CAs predating RFC 5280 conformance).
        aki = x509.AuthorityKeyIdentifier.from_issuer_public_key(cacert.public_key())  # type: ignore
    builder = builder.add_extension(aki, critical=False)
    # If CA and leaf cert have the same Subject Key Identifier, SChannel breaks in funny ways,
    # see https://github.com/mitmproxy/mitmproxy/issues/6494.
    # https://datatracker.ietf.org/doc/html/rfc5280#section-4.2.1.2 states
    # that SKI is optional for the leaf cert, so we skip that.

    if crl_url:
        builder = builder.add_extension(
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        [x509.UniformResourceIdentifier(crl_url)],
                        relative_name=None,
                        crl_issuer=None,
                        reasons=None,
                    )
                ]
            ),
            critical=False,
        )

    cert = builder.sign(private_key=privkey, algorithm=hashes.SHA256())  # type: ignore
    return Cert(cert)


def dummy_crl(
    privkey: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey,
    cacert: x509.Certificate,
) -> bytes:
    """
    Generates an empty CRL signed with the CA key

    privkey: CA private key
    cacert: CA certificate

    Returns a CRL DER encoded
    """
    builder = x509.CertificateRevocationListBuilder()
    builder = builder.issuer_name(cacert.issuer)

    now = datetime.datetime.now()
    builder = builder.last_update(now + CERT_VALIDITY_OFFSET)
    builder = builder.next_update(now + CERT_VALIDITY_OFFSET + CRL_EXPIRY)

    builder = builder.add_extension(x509.CRLNumber(1000), False)  # meaningless number
    crl = builder.sign(private_key=privkey, algorithm=hashes.SHA256())
    return crl.public_bytes(serialization.Encoding.DER)


@dataclass(frozen=True)
class CertStoreEntry:
    cert: Cert
    privatekey: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey
    chain_file: Path | None
    chain_certs: list[Cert]


TCustomCertId = str  # manually provided certs (e.g. mitmproxy's --certs)
TGeneratedCertId = tuple[Optional[str], x509.GeneralNames]  # (common_name, sans)
TCertId = Union[TCustomCertId, TGeneratedCertId]

DHParams = NewType("DHParams", bytes)


class CertStore:
    """
    Implements an in-memory certificate store.
    """

    STORE_CAP = 100
    default_privatekey: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey
    default_ca: Cert
    default_chain_file: Path | None
    default_chain_certs: list[Cert]
    dhparams: DHParams
    certs: dict[TCertId, CertStoreEntry]
    expire_queue: list[CertStoreEntry]

    def __init__(
        self,
        default_privatekey: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey,
        default_ca: Cert,
        default_chain_file: Path | None,
        default_crl: bytes,
        dhparams: DHParams,
    ):
        self.default_privatekey = default_privatekey
        self.default_ca = default_ca
        self.default_chain_file = default_chain_file
        self.default_crl = default_crl
        self.default_chain_certs = (
            [
                Cert(c)
                for c in x509.load_pem_x509_certificates(
                    self.default_chain_file.read_bytes()
                )
            ]
            if self.default_chain_file
            else [default_ca]
        )
        self.dhparams = dhparams
        self.certs = {}
        self.expire_queue = []

    def expire(self, entry: CertStoreEntry) -> None:
        self.expire_queue.append(entry)
        if len(self.expire_queue) > self.STORE_CAP:
            d = self.expire_queue.pop(0)
            self.certs = {k: v for k, v in self.certs.items() if v != d}

    @staticmethod
    def load_dhparam(path: Path) -> DHParams:
        # mitmproxy<=0.10 doesn't generate a dhparam file.
        # Create it now if necessary.
        if not path.exists():
            path.write_bytes(DEFAULT_DHPARAM)

        # we could use cryptography for this, but it's unclear how to convert cryptography's object to pyOpenSSL's
        # expected format.
        bio = OpenSSL.SSL._lib.BIO_new_file(  # type: ignore
            str(path).encode(sys.getfilesystemencoding()), b"r"
        )
        if bio != OpenSSL.SSL._ffi.NULL:  # type: ignore
            bio = OpenSSL.SSL._ffi.gc(bio, OpenSSL.SSL._lib.BIO_free)  # type: ignore
            dh = OpenSSL.SSL._lib.PEM_read_bio_DHparams(  # type: ignore
                bio,
                OpenSSL.SSL._ffi.NULL,  # type: ignore
                OpenSSL.SSL._ffi.NULL,  # type: ignore
                OpenSSL.SSL._ffi.NULL,  # type: ignore
            )
            dh = OpenSSL.SSL._ffi.gc(dh, OpenSSL.SSL._lib.DH_free)  # type: ignore
            return dh
        raise RuntimeError("Error loading DH Params.")  # pragma: no cover

    @classmethod
    def from_store(
        cls,
        path: Path | str,
        basename: str,
        key_size: int,
        passphrase: bytes | None = None,
    ) -> "CertStore":
        path = Path(path)
        ca_file = path / f"{basename}-ca.pem"
        dhparam_file = path / f"{basename}-dhparam.pem"
        if not ca_file.exists():
            cls.create_store(path, basename, key_size)
        return cls.from_files(ca_file, dhparam_file, passphrase)

    @classmethod
    def from_files(
        cls, ca_file: Path, dhparam_file: Path, passphrase: bytes | None = None
    ) -> "CertStore":
        raw = ca_file.read_bytes()
        key = load_pem_private_key(raw, passphrase)
        dh = cls.load_dhparam(dhparam_file)
        certs = x509.load_pem_x509_certificates(raw)
        ca = Cert(certs[0])
        crl = dummy_crl(key, ca._cert)
        if len(certs) > 1:
            chain_file: Path | None = ca_file
        else:
            chain_file = None
        return cls(key, ca, chain_file, crl, dh)

    @staticmethod
    @contextlib.contextmanager
    def umask_secret():
        """
        Context to temporarily set umask to its original value bitor 0o77.
        Useful when writing private keys to disk so that only the owner
        will be able to read them.
        """
        original_umask = os.umask(0)
        os.umask(original_umask | 0o77)
        try:
            yield
        finally:
            os.umask(original_umask)

    @staticmethod
    def create_store(
        path: Path, basename: str, key_size: int, organization=None, cn=None
    ) -> None:
        path.mkdir(parents=True, exist_ok=True)

        organization = organization or basename
        cn = cn or basename

        key: rsa.RSAPrivateKeyWithSerialization
        ca: x509.Certificate
        key, ca = create_ca(organization=organization, cn=cn, key_size=key_size)

        # Dump the CA plus private key.
        with CertStore.umask_secret():
            # PEM format
            (path / f"{basename}-ca.pem").write_bytes(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                + ca.public_bytes(serialization.Encoding.PEM)
            )

            # PKCS12 format for Windows devices
            (path / f"{basename}-ca.p12").write_bytes(
                pkcs12.serialize_key_and_certificates(  # type: ignore
                    name=basename.encode(),
                    key=key,
                    cert=ca,
                    cas=None,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # Dump the certificate in PEM format
        pem_cert = ca.public_bytes(serialization.Encoding.PEM)
        (path / f"{basename}-ca-cert.pem").write_bytes(pem_cert)
        # Create a .cer file with the same contents for Android
        (path / f"{basename}-ca-cert.cer").write_bytes(pem_cert)

        # Dump the certificate in PKCS12 format for Windows devices
        (path / f"{basename}-ca-cert.p12").write_bytes(
            pkcs12.serialize_key_and_certificates(
                name=basename.encode(),
                key=None,  # type: ignore
                cert=ca,
                cas=None,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        (path / f"{basename}-dhparam.pem").write_bytes(DEFAULT_DHPARAM)

    def add_cert_file(
        self, spec: str, path: Path, passphrase: bytes | None = None
    ) -> None:
        raw = path.read_bytes()
        cert = Cert.from_pem(raw)
        try:
            private_key = load_pem_private_key(raw, password=passphrase)
        except ValueError as e:
            private_key = self.default_privatekey
            if cert.public_key() != private_key.public_key():
                raise ValueError(
                    f'Unable to find private key in "{path.absolute()}": {e}'
                ) from e
        else:
            if cert.public_key() != private_key.public_key():
                raise ValueError(
                    f'Private and public keys in "{path.absolute()}" do not match:\n'
                    f"{cert.public_key()=}\n"
                    f"{private_key.public_key()=}"
                )

        try:
            chain = [Cert(x) for x in x509.load_pem_x509_certificates(raw)]
        except ValueError as e:
            logger.warning(f"Failed to read certificate chain: {e}")
            chain = [cert]

        if cert.is_ca:
            logger.warning(
                f'"{path.absolute()}" is a certificate authority and not a leaf certificate. '
                f"This indicates a misconfiguration, see https://docs.mitmproxy.org/stable/concepts-certificates/."
            )

        self.add_cert(CertStoreEntry(cert, private_key, path, chain), spec)

    def add_cert(self, entry: CertStoreEntry, *names: str) -> None:
        """
        Adds a cert to the certstore. We register the CN in the cert plus
        any SANs, and also the list of names provided as an argument.
        """
        if entry.cert.cn:
            self.certs[entry.cert.cn] = entry
        for i in entry.cert.altnames:
            self.certs[str(i.value)] = entry
        for i in names:
            self.certs[i] = entry

    @staticmethod
    def asterisk_forms(dn: str | x509.GeneralName) -> list[str]:
        """
        Return all asterisk forms for a domain. For example, for www.example.com this will return
        [b"www.example.com", b"*.example.com", b"*.com"]. The single wildcard "*" is omitted.
        """
        if isinstance(dn, str):
            parts = dn.split(".")
            ret = [dn]
            for i in range(1, len(parts)):
                ret.append("*." + ".".join(parts[i:]))
            return ret
        elif isinstance(dn, x509.DNSName):
            return CertStore.asterisk_forms(dn.value)
        else:
            return [str(dn.value)]

    def get_cert(
        self,
        commonname: str | None,
        sans: Iterable[x509.GeneralName],
        organization: str | None = None,
        crl_url: str | None = None,
    ) -> CertStoreEntry:
        """
        commonname: Common name for the generated certificate. Must be a
        valid, plain-ASCII, IDNA-encoded domain name.

        sans: A list of Subject Alternate Names.

        organization: Organization name for the generated certificate.

        crl_url: URL of CRL distribution point
        """
        sans = _fix_legacy_sans(sans)

        potential_keys: list[TCertId] = []
        if commonname:
            potential_keys.extend(self.asterisk_forms(commonname))
        for s in sans:
            potential_keys.extend(self.asterisk_forms(s))
        potential_keys.append("*")
        potential_keys.append((commonname, sans))

        name = next(filter(lambda key: key in self.certs, potential_keys), None)
        if name:
            entry = self.certs[name]
        else:
            entry = CertStoreEntry(
                cert=dummy_cert(
                    self.default_privatekey,
                    self.default_ca._cert,
                    commonname,
                    sans,
                    organization,
                    crl_url,
                ),
                privatekey=self.default_privatekey,
                chain_file=self.default_chain_file,
                chain_certs=self.default_chain_certs,
            )
            self.certs[(commonname, sans)] = entry
            self.expire(entry)

        return entry


def load_pem_private_key(
    data: bytes, password: bytes | None
) -> rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey:
    """
    like cryptography's load_pem_private_key, but silently falls back to not using a password
    if the private key is unencrypted.
    """
    try:
        return serialization.load_pem_private_key(data, password)  # type: ignore
    except TypeError:
        if password is not None:
            return load_pem_private_key(data, None)
        raise
