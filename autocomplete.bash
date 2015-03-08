#!/bin/bash

_mitmproxy() 
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="--help --anticache --version -h --conf --shortversion --cadir --host -q --quiet  -r  --read-flows "
    opts+="-s --script -t --stickycookie -u --stickyauth -v --verbose -w --wfile -a --afile -z --anticomp "
    opts+="-Z --body-size-limit --stream --palette -e --eventlog -b --bind-address -I --ignore --tcp -n --no-server "
    opts+="-p --port -R --reverse --socks -T --transparent -U --upstream --http-form-in --http-form-out --noapp "
    opts+="--app-host --app-port -c --client-replay -S --server-replay -k --kill --rheader --norefresh --no-pop "
    opts+="--replay-ignore-content --replay-ignore-payload-param --replay-ignore-param --replace --replace-from-file "
 	opts+="--setheader --nonanonymous --singleuser --htpasswd --cert --cert-forward --ciphers-client --ciphers-server " 
    opts+="--client-certs --no-upstream-cert --ssl-port --ssl-version-client --ssl-version-server -i --intercept " 

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _mitmproxy mitmproxy
complete -F _mitmproxy ./mitmproxy
