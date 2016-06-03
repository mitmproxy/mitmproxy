import React from "react"
import {render} from 'react-dom'
import {createStore} from 'redux'
import {Provider} from 'react-redux'

import $ from "jquery"
import Connection from "./connection"
import {App} from "./components/proxyapp.js"
import {EventLogActions} from "./actions.js"
import rootReducer from './ducks/index';

let store = createStore(rootReducer);

$(function () {
    window.ws = new Connection("/updates");

    window.onerror = function (msg) {
        EventLogActions.add_event(msg);
    };

    render(
        <Provider store={store}>{App}</Provider>,
        document.getElementById("mitmproxy"));
});

