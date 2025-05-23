/*
 * This backend uses the REST API only to host static instances,
 * without any Websocket connection.
 */
import { assertNever, fetchApi } from "../utils";
import { Store } from "redux";
import { RootState } from "../ducks";
import { OPTIONS_RECEIVE } from "../ducks/options";
import { FLOWS_RECEIVE } from "../ducks/flows";
import { Resource } from "./websocket";

export default class StaticBackend {
    store: Store<RootState>;

    constructor(store: Store<RootState>) {
        this.store = store;
        this.onOpen();
    }

    onOpen() {
        this.fetchData(Resource.Flows);
        this.fetchData(Resource.Options);
        // this.fetchData("events") # TODO: Add events log to static viewer.
    }

    fetchData(resource: Resource) {
        fetchApi(`./${resource}`)
            .then((res) => res.json())
            .then((json) => {
                this.receive(resource, json);
            });
    }

    receive(resource: Resource, data) {
        switch (resource) {
            case Resource.Flows:
                this.store.dispatch(FLOWS_RECEIVE(data));
                break;
            case Resource.Options:
                this.store.dispatch(OPTIONS_RECEIVE(data));
                break;
            /* istanbul ignore next @preserve */
            case Resource.State:
                throw "unreachable";
            /* istanbul ignore next @preserve */
            case Resource.Events:
                throw "unreachable";
            /* istanbul ignore next @preserve */
            default:
                assertNever(resource);
        }
    }
}
