/**
 *  The WebSocket backend is responsible for updating our knowledge of flows and events
 *  from the REST API and live updates delivered via a WebSocket connection.
 *  An alternative backend may use the REST API only to host static instances.
 */
import { fetchApi } from "../utils";
import * as connectionActions from "../ducks/connection";
import { Store } from "redux";
import { RootState } from "../ducks";
import { PayloadAction } from "@reduxjs/toolkit";
import { BackendState } from "../ducks/backendState";
import { serverFlowUpdate } from "../ducks/flows";

const CMD_RESET = "reset";

interface WebSocketMessage {
    cmd: string;
    resource: string;
    data?: any;
    expr?: string;
    matches?: Record<string, boolean>;
}

export default class WebsocketBackend {
    activeFetches: {
        flows?: [];
        events?: [];
        options?: [];
    };
    store: Store<RootState>;
    socket: WebSocket;
    messagesQueue: string[]; // Queue for messages while connecting.

    constructor(store) {
        this.activeFetches = {};
        this.store = store;
        this.messagesQueue = [];
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
        this.messagesQueue.forEach((message) => this.socket.send(message)); // Flush the message queue.
        this.messagesQueue = [];

        this.fetchData("state");
        this.fetchData("flows");
        this.fetchData("events");
        this.fetchData("options");
        this.store.dispatch(connectionActions.startFetching());
    }

    fetchData(resource: string) {
        const queue = [];
        this.activeFetches[resource] = queue;
        fetchApi(`./${resource}`)
            .then((res) => res.json())
            .then((json) => {
                // Make sure that we are not superseded yet by the server sending a RESET.
                if (this.activeFetches[resource] === queue)
                    this.receive(resource, json);
            });
    }

    onMessage(msg: WebSocketMessage) {
        console.log(msg);
        if (msg.cmd === CMD_RESET) {
            return this.fetchData(msg.resource);
        }
        if (msg.resource in this.activeFetches) {
            this.activeFetches[msg.resource].push(msg);
            return;
        }

        if (msg.resource === "flows") {
            if (msg.cmd === "update" || msg.cmd === "add") {
                console.log(msg.matches);
                if (msg.matches) {
                    this.store.dispatch(
                        serverFlowUpdate(msg.data, msg.matches),
                    );
                }
            } else {
                const type = `${msg.resource}_${msg.cmd}`.toUpperCase();
                this.store.dispatch({ type, ...msg });
            }
        } else {
            const type = `${msg.resource}_${msg.cmd}`.toUpperCase();
            this.store.dispatch({ type, ...msg });
        }
    }

    receive(resource: string, data: any) {
        const type = `${resource}_RECEIVE`.toUpperCase();
        if (resource === "state") {
            this.store.dispatch({
                type,
                payload: data,
            } as PayloadAction<BackendState>);
        } else {
            // deprecated: these should be converted to payload actions as well.
            this.store.dispatch({ type, cmd: "receive", resource, data });
        }
        const queue = this.activeFetches[resource];
        delete this.activeFetches[resource];
        queue.forEach((msg: WebSocketMessage) => this.onMessage(msg));

        if (Object.keys(this.activeFetches).length === 0) {
            // We have fetched the last resource
            this.store.dispatch(connectionActions.connectionEstablished());
        }
    }

    updateFilter(name: string, expr: string) {
        this.sendMessage("flows", {
            cmd: "updateFilter",
            name,
            expr,
        });
    }

    private sendMessage(resource: string, data: any) {
        const message = JSON.stringify({ resource, ...data });
        if (this.socket) {
            if (this.socket.readyState === WebSocket.CONNECTING) {
                this.messagesQueue.push(message);
            } else if (this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(message);
            } else {
                console.error(
                    "WebSocket is not open. Cannot send message:",
                    resource,
                    data,
                );
            }
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
