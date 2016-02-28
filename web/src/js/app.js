import React from "react"
import { render } from 'react-dom'
import $ from "jquery"
import Connection from "./connection"
import {app} from "./components/proxyapp.js"
import { EventLogActions } from "./actions.js"

$(function () {
    window.ws = new Connection("/updates");

    window.onerror = function (msg) {
        EventLogActions.add_event(msg);
    };

    render(app, document.getElementById("mitmproxy"));
});

