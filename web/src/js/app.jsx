import React from 'react'
import {render} from 'react-dom'
import {applyMiddleware, compose, createStore} from 'redux'
import {Provider} from 'react-redux'
import thunk from 'redux-thunk'

import ProxyApp from './components/ProxyApp'
import rootReducer from './ducks/index'
import {add as addLog} from './ducks/eventLog'
import useUrlState from './urlState'
import WebSocketBackend from './backends/websocket'
import StaticBackend from './backends/static'
import {logger} from 'redux-logger'


const middlewares = [thunk];

// logger must be last
if (process.env.NODE_ENV !== 'production') {
    middlewares.push(logger);
}


const composeEnhancers = window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;
const store = createStore(
    rootReducer,
    composeEnhancers(applyMiddleware(...middlewares))
)

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
