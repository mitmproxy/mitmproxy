import { ConnectionState } from "../../ducks/connection";
import { TDNSFlow, THTTPFlow, TTCPFlow, TUDPFlow } from "./_tflow";
import { RootState } from "../../ducks";
import { reducer } from "../../ducks/store";
import { DNSFlow, HTTPFlow, TCPFlow, UDPFlow } from "../../flow";
import { defaultState as defaultOptions } from "../../ducks/options";
import { TBackendState } from "./_tbackendstate";
import { configureStore } from "@reduxjs/toolkit";
import { Tab } from "../../ducks/ui/tabs";
import { LogLevel } from "../../ducks/eventLog";
import { ReverseProxyProtocols } from "../../backends/consts";
import { defaultReverseState } from "../../modes/reverse";

export { THTTPFlow as TFlow, TTCPFlow, TUDPFlow };

const tflow0: HTTPFlow = THTTPFlow();
const tflow1: HTTPFlow = THTTPFlow();
const tflow2: TCPFlow = TTCPFlow();
const tflow3: DNSFlow = TDNSFlow();
const tflow4: UDPFlow = TUDPFlow();
tflow0.modified = true;
tflow0.intercepted = true;
tflow1.id = "flow2";
tflow1.request.path = "/second";

export const testState: RootState = {
    backendState: TBackendState(),
    options_meta: {
        anticache: {
            type: "bool",
            default: false,
            value: false,
            help: "Strip out request headers that might cause the server to return 304-not-modified.",
            choices: undefined,
        },
        body_size_limit: {
            type: "optional str",
            default: undefined,
            value: undefined,
            help: "Byte size limit of HTTP request and response bodies. Understands k/m/g suffixes, i.e. 3m for 3 megabytes.",
            choices: undefined,
        },
        connection_strategy: {
            type: "str",
            default: "eager",
            value: "eager",
            help: "Determine when server connections should be established. When set to lazy, mitmproxy tries to defer establishing an upstream connection as long as possible. This makes it possible to use server replay while being offline. When set to eager, mitmproxy can detect protocols with server-side greetings, as well as accurately mirror TLS ALPN negotiation.",
            choices: ["eager", "lazy"],
        },
        listen_port: {
            type: "int",
            default: 8080,
            value: 8080,
            help: "Proxy service port.",
            choices: undefined,
        },
    },
    ui: {
        flow: {
            contentViewFor: {},
            tab: "request",
        },
        modal: {
            activeModal: undefined,
        },
        optionsEditor: {
            anticache: { isUpdating: true, error: false, value: true },
            cert_passphrase: {
                isUpdating: false,
                error: "incorrect password",
                value: "correcthorsebatterystaple",
            },
        },
        tabs: {
            current: Tab.Capture,
        },
    },
    options: defaultOptions,
    flows: {
        selected: [tflow1],
        selectedIndex: { [tflow1.id]: 0 },
        byId: {
            [tflow0.id]: tflow0,
            [tflow1.id]: tflow1,
            [tflow2.id]: tflow2,
            [tflow3.id]: tflow3,
            [tflow4.id]: tflow4,
        },
        filter: "~u /second | ~tcp | ~dns | ~udp",
        highlight: "~u /path",
        sort: {
            desc: true,
            column: "path",
        },
        view: [tflow1, tflow2, tflow3, tflow4],
        list: [tflow0, tflow1, tflow2, tflow3, tflow4],
        listIndex: {
            [tflow0.id]: 0,
            [tflow1.id]: 1,
            [tflow2.id]: 2,
            [tflow3.id]: 3,
            [tflow4.id]: 4,
        },
        viewIndex: {
            [tflow1.id]: 0,
            [tflow2.id]: 1,
            [tflow3.id]: 2,
            [tflow4.id]: 3,
        },
    },
    connection: {
        state: ConnectionState.ESTABLISHED,
    },
    eventLog: {
        visible: true,
        filters: {
            debug: true,
            info: true,
            web: false,
            warn: true,
            error: true,
        },
        view: [
            { id: "1", level: LogLevel.info, message: "foo" },
            { id: "2", level: LogLevel.error, message: "bar" },
        ],
        list: [
            { id: "1", level: LogLevel.info, message: "foo" },
            { id: "2", level: LogLevel.error, message: "bar" },
        ],
    },
    commandBar: {
        visible: false,
    },
    modes: {
        regular: [
            {
                active: true,
                ui_id: 1,
            },
        ],
        local: [
            {
                active: false,
                selectedProcesses: "",
                ui_id: 2,
            },
        ],
        wireguard: [
            {
                active: false,
                ui_id: 3,
            },
        ],
        reverse: [
            {
                active: false,
                protocol: ReverseProxyProtocols.HTTPS,
                destination: "example.com",
                ui_id: 4,
            },
            defaultReverseState(),
        ],
        transparent: [
            {
                active: false,
                ui_id: 5,
            },
        ],
        socks: [
            {
                active: false,
                ui_id: 6,
            },
        ],
        upstream: [
            {
                active: false,
                destination: "example.com",
                ui_id: 7,
            },
        ],
        dns: [
            {
                active: false,
                ui_id: 8,
            },
        ],
    },
    processes: {
        currentProcesses: [
            {
                is_visible: true,
                executable: "curl.exe",
                is_system: false,
                display_name: "curl",
            },
            {
                is_visible: true,
                executable: "http.exe",
                is_system: false,
                display_name: "http",
            },
        ],
        isLoading: false,
    },
};

export const TStore = () =>
    configureStore({
        reducer,
        preloadedState: testState,
        middleware: (getDefaultMiddleware) =>
            getDefaultMiddleware({
                immutableCheck: { warnAfter: 500_000 },
                serializableCheck: { warnAfter: 500_000 },
            }),
    });
