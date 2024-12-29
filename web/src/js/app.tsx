import * as React from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";

import ProxyApp from "./components/ProxyApp";
import { add as addLog } from "./ducks/eventLog";
import useUrlState from "./urlState";
import { store } from "./ducks";
import BackendSingleton from "./backends/BackendSingleton";

useUrlState(store);

BackendSingleton.getInstance(); // Initialize the backend singleton instance

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
