"""
Generate SSL test certificates.
"""
import subprocess
import shlex
import os
import shutil


ROOT_CA = "trusted-root"
SUBJECT = "/CN=127.0.0.1/"


def do(args):
    print("> %s" % args)
    args = shlex.split(args)
    output = subprocess.check_output(args)
    print(output)
    return output


def genrsa(cert):
    do("openssl genrsa -out {cert}.key 2048".format(cert=cert))


def sign(cert):
    do("openssl x509 -req -in {cert}.csr "
       "-CA {root_ca}.crt "
       "-CAkey {root_ca}.key "
       "-CAcreateserial "
       "-days 1024 "
       "-out {cert}.crt".format(root_ca=ROOT_CA, cert=cert)
       )


def mkcert(cert, args):
    genrsa(cert)
    do("openssl req -new -nodes -batch "
       "-key {cert}.key "
       "{args} "
       "-out {cert}.csr".format(cert=cert, args=args)
       )
    sign(cert)
    os.remove("{cert}.csr".format(cert=cert))


# create trusted root CA
genrsa("trusted-root")
do("openssl req -x509 -new -nodes -batch "
   "-key trusted-root.key "
   "-days 1024 "
   "-out trusted-root.crt"
   )
h = do("openssl x509 -hash -noout -in trusted-root.crt").strip()
shutil.copyfile("trusted-root.crt", "{}.0".format(h))

# create trusted leaf cert.
mkcert("trusted-leaf", "-subj {}".format(SUBJECT))

# create wrong host leaf cert.
mkcert("trusted-leaf-bad-host", "-subj /CN=wrong.host/")

# create self-signed cert
genrsa("self-signed")
do("openssl req -x509 -new -nodes -batch "
   "-key self-signed.key "
   "-subj {} "
   "-days 1024 "
   "-out self-signed.crt".format(SUBJECT)
   )


