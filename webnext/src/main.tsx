import "./globals.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app";
import initialize from "web/urlState";
import { add as addLog } from "web/ducks/eventLog";
import WebSocketBackend from "web/backends/websocket";
import { Provider } from "react-redux";
import { createStore } from "web/ducks/store";

const store = createStore("webnext");

// Extend the Window interface to avoid TS errors
declare global {
  interface Window {
    MITMWEB_STATIC?: boolean;
  }
}

if (window.MITMWEB_STATIC) {
  // @ts-expect-error this is not declared above as it should not be used.
  window.backend = new StaticBackend(store);
} else {
  // @ts-expect-error this is not declared above as it should not be used.
  window.backend = new WebSocketBackend(store);
}

initialize(store);

window.addEventListener("error", (e: ErrorEvent) => {
  store.dispatch(addLog(`${e.message}\n${e.error}`));
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
);
