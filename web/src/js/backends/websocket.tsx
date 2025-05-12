/**
 *  The WebSocket backend is responsible for updating our knowledge of flows and events
 *  from the REST API and live updates delivered via a WebSocket connection.
 *  An alternative backend may use the REST API only to host static instances.
 */
import { assertNever, fetchApi } from "../utils";
import * as connectionActions from "../ducks/connection";
import { Store } from "redux";
import { RootState } from "../ducks";
import { STATE_RECEIVE, STATE_UPDATE } from "../ducks/backendState";
import { EVENTS_ADD, EVENTS_RECEIVE } from "../ducks/eventLog";
import { OPTIONS_RECEIVE, OPTIONS_UPDATE } from "../ducks/options";
import {
    FLOWS_ADD,
    FLOWS_RECEIVE,
    FLOWS_REMOVE,
    FLOWS_UPDATE,
} from "../ducks/flows";
import { Action } from "@reduxjs/toolkit";

export enum Resource {
    State = "state",
    Flows = "flows",
    Events = "events",
    Options = "options",
}

/// All possible events emitted by the WebSocket backend.
type WebsocketMessageType =
    | "flows/add"
    | "flows/update"
    | "flows/remove"
    | "flows/reset"
    | "events/add"
    | "events/reset"
    | "options/update"
    | "state/update";

export default class WebsocketBackend {
    activeFetches: Partial<{ [key in Resource]: Array<Action> }>;
    store: Store<RootState>;
    socket: WebSocket;
    messageQueue: Action[];

    constructor(store) {
        this.activeFetches = {};
        this.store = store;
        this.messageQueue = [];
        this.connect();
    }

    connect() {
        this.socket = new WebSocket(
            location.origin.replace("http", "ws") +
                location.pathname.replace(/\/$/, "") +
                "/updates",
        );
        this.socket.addEventListener("open", () => this.onOpen());
        this.socket.addEventListener("close", (event) => this.onClose(event));
        this.socket.addEventListener("message", (msg) =>
            this.onMessage(JSON.parse(msg.data)),
        );
        this.socket.addEventListener("error", (error) => this.onError(error));
    }

    onOpen() {
        for (const message of this.messageQueue) {
            this.socket.send(JSON.stringify(message));
        }
        this.messageQueue = [];
        this.fetchData(Resource.State);
        this.fetchData(Resource.Flows);
        this.fetchData(Resource.Events);
        this.fetchData(Resource.Options);
        this.store.dispatch(connectionActions.startFetching());
    }

    fetchData(resource: Resource) {
        const queue: Array<Action> = [];
        this.activeFetches[resource] = queue;
        fetchApi(`./${resource}`)
            .then((res) => res.json())
            .then((json) => {
                // Make sure that we are not superseded yet by the server sending a RESET.
                if (this.activeFetches[resource] === queue)
                    this.receive(resource, json);
            });
    }

    onMessage(msg: { type: WebsocketMessageType; payload?: any }) {
        switch (msg.type) {
            case "flows/add":
                return this.queueOrDispatch(
                    Resource.Flows,
                    FLOWS_ADD(msg.payload),
                );
            case "flows/update":
                return this.queueOrDispatch(
                    Resource.Flows,
                    FLOWS_UPDATE(msg.payload),
                );
            case "flows/remove":
                return this.queueOrDispatch(
                    Resource.Flows,
                    FLOWS_REMOVE(msg.payload),
                );
            case "events/add":
                return this.queueOrDispatch(
                    Resource.Events,
                    EVENTS_ADD(msg.payload),
                );
            case "options/update":
                return this.queueOrDispatch(
                    Resource.Options,
                    OPTIONS_UPDATE(msg.payload),
                );
            case "state/update":
                return this.queueOrDispatch(
                    Resource.State,
                    STATE_UPDATE(msg.payload),
                );
            case "flows/reset":
                return this.fetchData(Resource.Flows);
            case "events/reset":
                return this.fetchData(Resource.Events);
            /* istanbul ignore next @preserve */
            default:
                assertNever(msg.type);
        }
    }

    sendMessage(action: Action) {
        if (this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(action));
        } else if (this.socket.readyState === WebSocket.CONNECTING) {
            this.messageQueue.push(action);
        } else {
            console.error("WebSocket is not open. Cannot send:", action);
        }
    }

    queueOrDispatch(resource: Resource, action: Action) {
        const queue = this.activeFetches[resource];
        if (queue !== undefined) {
            queue.push(action);
        } else {
            this.store.dispatch(action);
        }
    }

    receive(resource: Resource, data) {
        switch (resource) {
            case Resource.State:
                this.store.dispatch(STATE_RECEIVE(data));
                break;
            case Resource.Options:
                this.store.dispatch(OPTIONS_RECEIVE(data));
                break;
            case Resource.Events:
                this.store.dispatch(EVENTS_RECEIVE(data));
                break;
            case Resource.Flows:
                this.store.dispatch(FLOWS_RECEIVE(data));
                break;
            /* istanbul ignore next @preserve */
            default:
                assertNever(resource);
        }
        const queue = this.activeFetches[resource]!;
        delete this.activeFetches[resource];
        queue.forEach((msg) => this.store.dispatch(msg));

        if (Object.keys(this.activeFetches).length === 0) {
            // We have fetched the last resource
            this.store.dispatch(connectionActions.connectionEstablished());
        }
    }

    onClose(closeEvent: CloseEvent) {
        this.store.dispatch(
            connectionActions.connectionError(
                `Connection closed at ${new Date().toUTCString()} with error code ${
                    closeEvent.code
                }.`,
            ),
        );
        console.error("websocket connection closed", closeEvent);
    }

    onError(...args) {
        // FIXME
        console.error("websocket connection errored", args);
    }
}
