import StaticBackend from "./static";
import { store } from "../ducks";
import WebSocketBackend from "./websocket";

export const backend = window.MITMWEB_STATIC
    ? new StaticBackend(store)
    : new WebSocketBackend(store);
