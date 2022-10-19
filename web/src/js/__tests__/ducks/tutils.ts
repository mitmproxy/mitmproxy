import thunk from 'redux-thunk'
import configureStore, {MockStoreCreator, MockStoreEnhanced} from 'redux-mock-store'
import {ConnectionState} from '../../ducks/connection'
import {TDNSFlow, THTTPFlow, TTCPFlow, TUDPFlow} from './_tflow'
import {AppDispatch, RootState} from "../../ducks";
import {DNSFlow, HTTPFlow, TCPFlow, UDPFlow} from "../../flow";
import {defaultState as defaultOptions} from "../../ducks/options"
import {TBackendState} from "./_tbackendstate"

const mockStoreCreator: MockStoreCreator<RootState, AppDispatch> = configureStore([thunk])

export {THTTPFlow as TFlow, TTCPFlow, TUDPFlow}

const tflow0: HTTPFlow = THTTPFlow();
const tflow1: HTTPFlow = THTTPFlow();
const tflow2: TCPFlow = TTCPFlow();
const tflow3: DNSFlow = TDNSFlow();
const tflow4: UDPFlow = TUDPFlow();
tflow0.modified = true
tflow0.intercepted = true
tflow1.id = "flow2";
tflow1.request.path = "/second";

export const testState: RootState = {
    backendState: TBackendState(),
    options_meta: {
        anticache: {
            "type": "bool",
            "default": false,
            "value": false,
            "help": "Strip out request headers that might cause the server to return 304-not-modified.",
            "choices": undefined
        },
        body_size_limit: {
            "type": "optional str",
            "default": undefined,
            "value": undefined,
            "help": "Byte size limit of HTTP request and response bodies. Understands k/m/g suffixes, i.e. 3m for 3 megabytes.",
            "choices": undefined,
        },
        connection_strategy: {
            "type": "str",
            "default": "eager",
            "value": "eager",
            "help": "Determine when server connections should be established. When set to lazy, mitmproxy tries to defer establishing an upstream connection as long as possible. This makes it possible to use server replay while being offline. When set to eager, mitmproxy can detect protocols with server-side greetings, as well as accurately mirror TLS ALPN negotiation.",
            "choices": [
                "eager",
                "lazy"
            ]
        },
        listen_port: {
            "type": "int",
            "default": 8080,
            "value": 8080,
            "help": "Proxy service port.",
            "choices": undefined
        }
    },
    ui: {
        flow: {
            contentViewFor: {},
            tab: 'request'
        },
        modal: {
            activeModal: undefined
        },
        optionsEditor: {
            booleanOption: {isUpdating: true, error: false},
            strOption: {error: true},
            intOption: {},
            choiceOption: {},
        }
    },
    options: defaultOptions,
    flows: {
        selected: [tflow1.id],
        byId: {
            [tflow0.id]: tflow0,
            [tflow1.id]: tflow1,
            [tflow2.id]: tflow2,
            [tflow3.id]: tflow3,
            [tflow4.id]: tflow4,
        },
        filter: '~u /second | ~tcp | ~dns | ~udp',
        highlight: '~u /path',
        sort: {
            desc: true,
            column: "path"
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
        state: ConnectionState.ESTABLISHED
    },
    eventLog: {
        visible: true,
        filters: {
            debug: true,
            info: true,
            web: false,
            warn: true,
            error: true
        },
        view: [
            {id: "1", level: 'info', message: 'foo'},
            {id: "2", level: 'error', message: 'bar'}
        ],
        byId: {}, // TODO: incomplete
        list: [],  // TODO: incomplete
        listIndex: {},  // TODO: incomplete
        viewIndex: {},  // TODO: incomplete
    },
    commandBar: {
        visible: false,
    }
}


export function TStore(): MockStoreEnhanced<RootState, AppDispatch> {
    return mockStoreCreator(testState)
}
