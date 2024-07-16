import initialize, {
    updateStoreFromUrl,
    updateUrlFromStore,
} from "../urlState";

import reduceFlows, * as flowsActions from "../ducks/flows";
import reduceUI from "../ducks/ui/index";
import reduceEventLog from "../ducks/eventLog";
import reduceCommandBar from "../ducks/commandBar";

import configureStore from "redux-mock-store";

const mockStore = configureStore();
history.replaceState = jest.fn();

describe("updateStoreFromUrl", () => {
    it("should handle search query", () => {
        window.location.hash = "#/flows?s=foo";
        const store = mockStore();
        updateStoreFromUrl(store);
        expect(store.getActions()).toEqual([
            { filter: "foo", type: "FLOWS_SET_FILTER" },
        ]);
    });

    it("should handle highlight query", () => {
        window.location.hash = "#/flows?h=foo";
        const store = mockStore();
        updateStoreFromUrl(store);
        expect(store.getActions()).toEqual([
            { highlight: "foo", type: "FLOWS_SET_HIGHLIGHT" },
        ]);
    });

    it("should handle show event log", () => {
        window.location.hash = "#/flows?e=true";
        const initialState = { eventLog: reduceEventLog(undefined, {}) };
        const store = mockStore(initialState);
        updateStoreFromUrl(store);
        expect(store.getActions()).toEqual([
            { type: "EVENTS_TOGGLE_VISIBILITY" },
        ]);
    });

    it("should handle unimplemented query argument", () => {
        window.location.hash = "#/flows?foo=bar";
        console.error = jest.fn();
        const store = mockStore();
        updateStoreFromUrl(store);
        expect(console.error).toBeCalledWith(
            "unimplemented query arg: foo=bar",
        );
    });

    it("should select flow and tab", () => {
        window.location.hash = "#/flows/123/request";
        const store = mockStore();
        updateStoreFromUrl(store);
        expect(store.getActions()).toEqual([
            {
                flowIds: ["123"],
                type: "FLOWS_SELECT",
            },
            {
                tab: "request",
                type: "UI_FLOWVIEW_SET_TAB",
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
        updateUrlFromStore(store);
        expect(history.replaceState).toBeCalledWith(undefined, "", "/#/flows");
    });

    it("should update url", () => {
        const flows = reduceFlows(undefined, flowsActions.select("123"));
        const state = {
            ...initialState,
            flows: reduceFlows(flows, flowsActions.setFilter("~u foo")),
        };
        const store = mockStore(state);
        updateUrlFromStore(store);
        expect(history.replaceState).toBeCalledWith(
            undefined,
            "",
            "/#/flows/123/request?s=~u%20foo",
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
