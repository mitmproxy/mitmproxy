import initialize, {
    updateStoreFromUrl,
    updateUrlFromStore,
} from "../urlState";

import reduceFlows from "../ducks/flows";
import reduceUI from "../ducks/ui/index";
import reduceEventLog from "../ducks/eventLog";
import reduceCommandBar from "../ducks/commandBar";

import configureStore from "redux-mock-store";
import {testState} from "./ducks/tutils";
import {RootStore} from "../ducks/store";

const mockStore = configureStore();
history.replaceState = jest.fn();

describe("updateStoreFromUrl", () => {
    it("should handle search query", () => {
        window.location.hash = "#/flows?s=foo";
        const store = mockStore(testState);
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([
            { filter: "foo", type: "FLOWS_SET_FILTER" },
        ]);
    });

    it("should handle highlight query", () => {
        window.location.hash = "#/flows?h=foo";
        const store = mockStore();
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([
            { highlight: "foo", type: "FLOWS_SET_HIGHLIGHT" },
        ]);
    });

    it("should handle show event log", () => {
        window.location.hash = "#/flows?e=true";
        const initialState = { eventLog: reduceEventLog(undefined, {}) };
        const store = mockStore(initialState);
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([
            { type: "EVENTS_TOGGLE_VISIBILITY" },
        ]);
    });

    it("should handle unimplemented query argument", () => {
        window.location.hash = "#/flows?foo=bar";
        console.error = jest.fn();
        const store = mockStore();
        updateStoreFromUrl(store as RootStore);
        expect(console.error).toBeCalledWith(
            "unimplemented query arg: foo=bar",
        );
    });

    it("should select flow and tab", () => {
        const tflow0 = testState.flows.list[0];
        window.location.hash = `#/flows/${tflow0.id}/request`;
        const store = mockStore(testState);
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([
            {
                payload: "request",
                type: "ui/flow/selectTab",
            },
            {
                flows: [tflow0],
                type: "FLOWS_SELECT",
            },
        ]);
    });
});

describe("updateUrlFromStore", () => {
    const initialState = {
        flows: reduceFlows(undefined, { type: "other" }),
        ui: reduceUI(undefined, { type: "other" }),
        eventLog: reduceEventLog(undefined, { type: "other" }),
        commandBar: reduceCommandBar(undefined, { type: "other" }),
    };

    it("should update initial url", () => {
        const store = mockStore(initialState);
        updateUrlFromStore(store as RootStore);
        expect(history.replaceState).toBeCalledWith(undefined, "", "/#/flows");
    });

    it("should update url", () => {
        const store = mockStore(testState);
        updateUrlFromStore(store as RootStore);
        expect(history.replaceState).toBeCalledWith(
            undefined,
            "",
            "/#/flows/flow2/request?s=~u%20%2Fsecond%20%7C%20~tcp%20%7C%20~dns%20%7C%20~udp&h=~u%20%2Fpath&e=true",
        );
    });
});

describe("initialize", () => {
    const initialState = {
        flows: reduceFlows(undefined, { type: "other" }),
        ui: reduceUI(undefined, { type: "other" }),
        eventLog: reduceEventLog(undefined, { type: "other" }),
        commandBar: reduceCommandBar(undefined, { type: "other" }),
    };

    it("should handle initial state", () => {
        const store = mockStore(initialState);
        initialize(store);
        store.dispatch({ type: "foo" });
    });
});
