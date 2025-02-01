import re
import sys

DEPRECATED = """
--confdir
-Z
--body-size-limit
--stream
--palette
--palette-transparent
--follow
--order
--no-mouse
--reverse
--http2-priority
--no-http2-priority
--no-websocket
--websocket
--upstream-bind-address
--ciphers-client
--ciphers-server
--client-certs
--no-upstream-cert
--add-upstream-certs-to-client-chain
--upstream-trusted-confdir
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
--replacements
-i
-f
--filter
--socks
--server-replay-nopop
"""

REPLACEMENTS = {
    "--stream": "stream_large_bodies",
    "--palette": "console_palette",
    "--palette-transparent": "console_palette_transparent:",
    "--follow": "console_focus_follow",
    "--order": "view_order",
    "--no-mouse": "console_mouse",
    "--reverse": "view_order_reversed",
    "--no-websocket": "websocket",
    "--no-upstream-cert": "upstream_cert",
    "--upstream-trusted-confdir": "ssl_verify_upstream_trusted_confdir",
    "--upstream-trusted-ca": "ssl_verify_upstream_trusted_ca",
    "--no-onboarding": "onboarding",
    "--no-pop": "server_replay_reuse",
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
    "--replace": ["--modify-body", "--modify-headers"],
    "--replacements": ["--modify-body", "--modify-headers"],
    "-i": "--intercept",
    "-f": "--view-filter",
    "--filter": "--view-filter",
    "--socks": "--mode socks5",
    "--server-replay-nopop": "--server-replay-reuse",
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
            print(f"{option} has been removed.")

    for option in ("--nonanonymous", "--singleuser", "--htpasswd"):
        if option in args:
            print(
                "{} is deprecated.\n"
                "Please use `--proxyauth SPEC` instead.\n"
                'SPEC Format: "username:pass", "any" to accept any user/pass combination,\n'
                '"@path" to use an Apache htpasswd file, or\n'
                '"ldap[s]:url_server_ldap[:port]:dn_auth:password:dn_subtree[?search_filter_key=...]" '
                "for LDAP authentication.".format(option)
            )

    for option in REPLACED.splitlines():
        if option in args:
            r = REPLACEMENTS.get(option)
            if isinstance(r, list):
                new_options = r
            else:
                new_options = [r]
            print(
                "{} is deprecated.\nPlease use `{}` instead.".format(
                    option, "` or `".join(new_options)
                )
            )

    for option in DEPRECATED.splitlines():
        if option in args:
            print(
                "{} is deprecated.\n"
                "Please use `--set {}=value` instead.\n"
                "To show all options and their default values use --options".format(
                    option,
                    REPLACEMENTS.get(option, None)
                    or option.lstrip("-").replace("-", "_"),
                )
            )

    # Check for underscores in the options. Options always follow '--'.
    for argument in args:
        underscoreParam = re.search(r"[-]{2}((.*?_)(.*?(\s|$)))+", argument)
        if underscoreParam is not None:
            print(
                "{} uses underscores, please use hyphens {}".format(
                    argument, argument.replace("_", "-")
                )
            )
