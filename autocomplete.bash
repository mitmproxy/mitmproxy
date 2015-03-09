#!/bin/bash

_base_mitmproxy() 
{
    local cur prev opts extra_opts
    extra_opts="$1"
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    opts="--help --anticache --version -h --conf --shortversion --cadir --host -q --quiet  -r  --read-flows "
    opts+="-s --script -t --stickycookie -u --stickyauth -v --verbose -w --wfile -a --afile -z --anticomp "
    opts+="-Z --body-size-limit --stream -b --bind-address -I --ignore --tcp -n --no-server "
    opts+="-p --port -R --reverse --socks -T --transparent -U --upstream --http-form-in --http-form-out --noapp "
    opts+="--app-host --app-port -c --client-replay -S --server-replay -k --kill --rheader --norefresh --no-pop "
    opts+="--replay-ignore-content --replay-ignore-payload-param --replay-ignore-param --replace --replace-from-file "
    opts+="--setheader --nonanonymous --singleuser --htpasswd --cert --cert-forward --ciphers-client --ciphers-server " 
    opts+="--client-certs --no-upstream-cert --ssl-port --ssl-version-client --ssl-version-server " 

    opts+="$extra_opts"

    case "${prev}" in
        --conf | -r | --read-flows | -w | --wfile | -a | --afile | -c | --client-replay | -S | --server-replay | --replace-from-file )
            _filedir
            return 0
            ;;
         
        --cadir | --client-certs)
            _filedir -d
            return 0
            ;;
        -s | --script)
            _filedir py
            return 0
            ;;
        --palette)
            COMPREPLY=( $(compgen -W "dark light solarized_dark solarized_light" -- ${cur}) )
            return 0
            ;;
        --http-form-in | --http-form-out)
            COMPREPLY=( $(compgen -W "relative absolute" -- ${cur}) )
            return 0
            ;;
        --ssl-version-client | --ssl-version-server)
            COMPREPLY=( $(compgen -W "all secure SSLv2 SSLv3 TLSv1 TLSv1_1 TLSv1_2" -- ${cur}) )
            return 0
            ;;
        *)
        ;;
    esac

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}

_mitmproxy() {
    local opts
    opts="--palette -e --eventlog -i --intercept "
    _base_mitmproxy "$opts"
}

_mitmdump() {
    local opts
    opts="--keepserving -d --detail "
    _base_mitmproxy "$opts"
}

_mitmweb() {
    local opts
    opts="--wport --wiface --wdebug -i --intercept "
    _base_mitmproxy "$opts"
}

complete -F _mitmproxy mitmproxy
complete -F _mitmdump mitmdump
complete -F _mitmweb mitmweb
