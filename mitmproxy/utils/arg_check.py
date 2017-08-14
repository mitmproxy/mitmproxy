import sys

DEPRECATED = """
--cadir
-Z
--body-size-limit
--stream
--palette
--palette-transparent
--follow
--order
--no-mouse
--reverse
--socks
--http2-priority
--no-http2-priority
--no-websocket
--websocket
--spoof-source-address
--upstream-bind-address
--ciphers-client
--ciphers-server
--client-certs
--no-upstream-cert
--add-upstream-certs-to-client-chain
--upstream-trusted-cadir
--upstream-trusted-ca
--ssl-version-client
--ssl-version-server
--no-onboarding
--onboarding-host
--onboarding-port
--server-replay-use-header
--no-pop
--replay-ignore-content
--replay-ignore-payload-param
--replay-ignore-param
--replay-ignore-host
--replace-from-file
"""

REPLACED = """
-t
-u
--wfile
-a
--afile
-z
-b
--bind-address
--port
-I
--ignore
--tcp
--cert
--insecure
-c
--replace
-i
-f
--filter
"""

REPLACEMENTS = {
    "--stream": "stream_large_bodies",
    "--palette": "console_palette",
    "--palette-transparent": "console_palette_transparent:",
    "--follow": "console_focus_follow",
    "--order": "console_order",
    "--no-mouse": "console_mouse",
    "--reverse": "console_order_reversed",
    "--no-http2-priority": "http2_priority",
    "--no-websocket": "websocket",
    "--no-upstream-cert": "upstream_cert",
    "--upstream-trusted-cadir": "ssl_verify_upstream_trusted_cadir",
    "--upstream-trusted-ca": "ssl_verify_upstream_trusted_ca",
    "--no-onboarding": "onboarding",
    "--no-pop": "server_replay_nopop",
    "--replay-ignore-content": "server_replay_ignore_content",
    "--replay-ignore-payload-param": "server_replay_ignore_payload_params",
    "--replay-ignore-param": "server_replay_ignore_params",
    "--replay-ignore-host": "server_replay_ignore_host",
    "--replace-from-file": "replacements (use @ to specify path)",
    "-t": "--stickycookie",
    "-u": "--stickyauth",
    "--wfile": "--save-stream-file",
    "-a": "-w  Prefix path with + to append.",
    "--afile": "-w  Prefix path with + to append.",
    "-z": "--anticomp",
    "-b": "--listen-host",
    "--bind-address": "--listen-host",
    "--port": "--listen-port",
    "-I": "--ignore-hosts",
    "--ignore": "--ignore-hosts",
    "--tcp": "--tcp-hosts",
    "--cert": "--certs",
    "--insecure": "--ssl-insecure",
    "-c": "-C",
    "--replace": "--replacements",
    "-i": "--intercept",
    "-f": "--view-filter",
    "--filter": "--view-filter"
}


def check():
    args = sys.argv[1:]
    print()
    if "-U" in args:
        print("-U is deprecated, please use --mode upstream:SPEC instead")

    if "-T" in args:
        print("-T is deprecated, please use --mode transparent instead")

    for option in ("-e", "--eventlog", "--norefresh"):
        if option in args:
            print("{} has been removed.".format(option))

    for option in ("--nonanonymous", "--singleuser", "--htpasswd"):
        if option in args:
            print(
                '{} is deprecated.\n'
                'Please use `--proxyauth SPEC` instead.\n'
                'SPEC Format: "username:pass", "any" to accept any user/pass combination,\n'
                '"@path" to use an Apache htpasswd file, or\n'
                '"ldap[s]:url_server_ldap:dn_auth:password:dn_subtree" '
                'for LDAP authentication.'.format(option))

    for option in REPLACED.splitlines():
        if option in args:
            print(
                "{} is deprecated.\n"
                "Please use `{}` instead.".format(
                    option,
                    REPLACEMENTS.get(option)
                )
            )

    for option in DEPRECATED.splitlines():
        if option in args:
            print(
                "{} is deprecated.\n"
                "Please use `--set {}=value` instead.\n"
                "To show all options and their default values use --options".format(
                    option,
                    REPLACEMENTS.get(option, None) or option.lstrip("-").replace("-", "_")
                )
            )
