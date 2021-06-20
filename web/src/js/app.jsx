import React from 'react'
import {render} from 'react-dom'
import {Provider} from 'react-redux'

import ProxyApp from './components/ProxyApp'
import {add as addLog} from './ducks/eventLog'
import useUrlState from './urlState'
import WebSocketBackend from './backends/websocket'
import StaticBackend from './backends/static'
import {store} from "./ducks";


useUrlState(store)
if (window.MITMWEB_STATIC) {
    window.backend = new StaticBackend(store)
} else {
    window.backend = new WebSocketBackend(store)
}

window.addEventListener('error', msg => {
    store.dispatch(addLog(msg))
})

document.addEventListener('DOMContentLoaded', () => {
    render(
        <Provider store={store}>
            <ProxyApp/>
        </Provider>,
        document.getElementById("mitmproxy")
    )
})
