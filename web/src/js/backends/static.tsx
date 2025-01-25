/*
 * This backend uses the REST API only to host static instances,
 * without any Websocket connection.
 */
import { fetchApi } from "../utils";
import { Store } from "redux";
import { RootState } from "../ducks";

export default class StaticBackend {
    store: Store<RootState>;

    constructor(store) {
        this.store = store;
        this.onOpen();
    }

    onOpen() {
        this.fetchData("flows");
        this.fetchData("options");
        // this.fetchData("events") # TODO: Add events log to static viewer.
    }

    fetchData(resource) {
        fetchApi(`./${resource}`)
            .then((res) => res.json())
            .then((json) => {
                this.receive(resource, json);
            });
    }

    receive(resource, data) {
        const type = `${resource}_RECEIVE`.toUpperCase();
        this.store.dispatch({ type, cmd: "receive", resource, data });
    }
}
