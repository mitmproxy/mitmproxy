import React from "react"
import {render} from 'react-dom'
import {applyMiddleware, createStore} from 'redux'
import {Provider} from 'react-redux'
import createLogger from 'redux-logger';

import Connection from "./connection"
import {App} from "./components/proxyapp.js"
import rootReducer from './ducks/index';
import {addLogEntry} from "./ducks/eventLog";

// logger must be last
const logger = createLogger();
const store = createStore(rootReducer, applyMiddleware(logger));

window.onerror = function (msg) {
    store.dispatch(addLogEntry(msg));
};

document.addEventListener('DOMContentLoaded', () => {
    window.ws = new Connection("/updates", store.dispatch);

    render(
        <Provider store={store}>{App}</Provider>,
        document.getElementById("mitmproxy")
    );

});
