import WebsocketBackend from "./websocket";
import { store } from "../ducks";
import StaticBackend from "./static";

class BackendSingleton {
    private static instance: WebsocketBackend | StaticBackend;

    private constructor() {}

    static getInstance(): WebsocketBackend | StaticBackend {
        if (!BackendSingleton.instance) {
            // @ts-expect-error custom property on window
            if (window.MITMWEB_STATIC) {
                BackendSingleton.instance = new StaticBackend(store);
            } else {
                BackendSingleton.instance = new WebsocketBackend(store);
            }
        }
        return BackendSingleton.instance;
    }
}

export default BackendSingleton;
