import initialize, {
    updateStoreFromUrl,
    updateUrlFromStore,
} from "../urlState";

import reduceFlows, * as flowActions from "../ducks/flows";
import reduceUI from "../ducks/ui/index";
import reduceEventLog, * as eventLogActions from "../ducks/eventLog";
import reduceCommandBar from "../ducks/commandBar";

import configureStore from "redux-mock-store";
import { testState } from "./ducks/tutils";
import { RootStore } from "../ducks/store";
import { setCurrent, Tab } from "../ducks/ui/tabs";
import { selectTab } from "../ducks/ui/flow";

const mockStore = configureStore();
history.replaceState = jest.fn();

describe("updateStoreFromUrl", () => {
    it("should handle search query", () => {
        window.location.hash = "#/flows?s=foo";
        const store = mockStore(testState);
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([flowActions.setFilter("foo")]);
    });

    it("should handle highlight query", () => {
        window.location.hash = "#/flows?h=foo";
        const store = mockStore();
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([flowActions.setHighlight("foo")]);
    });

    it("should handle show event log", () => {
        window.location.hash = "#/flows?e=true";
        const initialState = {
            eventLog: reduceEventLog(undefined, { type: "unknown" }),
        };
        const store = mockStore(initialState);
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([
            eventLogActions.toggleVisibility(),
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
            selectTab("request"),
            flowActions.select([tflow0]),
        ]);
    });

    it("should handle capture tab", () => {
        window.location.hash = "#/capture";
        const store = mockStore();
        updateStoreFromUrl(store as RootStore);
        expect(store.getActions()).toEqual([setCurrent(Tab.Capture)]);
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
            "/#/capture?s=~u%20%2Fsecond%20%7C%20~tcp%20%7C%20~dns%20%7C%20~udp&h=~u%20%2Fpath&e=true",
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
