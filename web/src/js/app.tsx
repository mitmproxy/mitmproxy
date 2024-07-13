import * as React from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";

import ProxyApp from "./components/ProxyApp";
import { add as addLog } from "./ducks/eventLog";
import useUrlState from "./urlState";
import WebSocketBackend from "./backends/websocket";
import StaticBackend from "./backends/static";
import { store } from "./ducks";

useUrlState(store);
// @ts-expect-error custom property on window
if (window.MITMWEB_STATIC) {
    // @ts-expect-error new property on window for debugging
    window.backend = new StaticBackend(store);
} else {
    // @ts-expect-error new property on window for debugging
    window.backend = new WebSocketBackend(store);
}

window.addEventListener("error", (e: ErrorEvent) => {
    store.dispatch(addLog(`${e.message}\n${e.error.stack}`));
});

document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("mitmproxy");
    const root = createRoot(container!);
    root.render(
        <Provider store={store}>
            <ProxyApp />
        </Provider>,
    );
});
