import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./globals.css";
import { App } from "./app";
import initialize from "web/urlState";
import { store } from "web/ducks/store";
import { add as addLog } from "web/ducks/eventLog";
import { Provider } from "react-redux";

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
