import * as React from "react"
import {render} from 'react-dom'
import {Provider} from 'react-redux'

import ProxyApp from './components/ProxyApp'
import {add as addLog} from './ducks/eventLog'
import useUrlState from './urlState'
import WebSocketBackend from './backends/websocket'
import StaticBackend from './backends/static'
import {store} from "./ducks";


useUrlState(store)
// @ts-ignore
if (window.MITMWEB_STATIC) {
    // @ts-ignore
    window.backend = new StaticBackend(store)
} else {
    // @ts-ignore
    window.backend = new WebSocketBackend(store)
}

window.addEventListener('error', (e: ErrorEvent) => {
    store.dispatch(addLog(`${e.message}\n${e.error.stack}`))
})

document.addEventListener('DOMContentLoaded', () => {
    render(
        <Provider store={store}>
            <ProxyApp/>
        </Provider>,
        document.getElementById("mitmproxy")
    )
})
