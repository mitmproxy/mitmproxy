import React from "react"
import { render } from 'react-dom'
import { applyMiddleware, createStore } from 'redux'
import { Provider } from 'react-redux'
import createLogger from 'redux-logger'
import thunkMiddleware from 'redux-thunk'
import { Route, Router as ReactRouter, hashHistory, Redirect } from "react-router"

import Connection from "./connection"
import ProxyApp from "./components/ProxyApp"
import MainView from './components/MainView'
import rootReducer from './ducks/index'
import { add as addLog } from "./ducks/eventLog"

// logger must be last
const store = createStore(
    rootReducer,
    applyMiddleware(thunkMiddleware, createLogger())
)

window.addEventListener('error', msg => {
    store.dispatch(addLog(msg))
})

// @todo remove this
document.addEventListener('DOMContentLoaded', () => {
    window.ws = new Connection("/updates", store.dispatch)

    render(
        <Provider store={store}>
            <ReactRouter history={hashHistory}>
                <Redirect from="/" to="/flows" />
                <Route path="/" component={ProxyApp}>
                    <Route path="flows" component={MainView}/>
                    <Route path="flows/:flowId/:detailTab" component={MainView}/>
                </Route>
            </ReactRouter>
        </Provider>,
        document.getElementById("mitmproxy")
    )
})
