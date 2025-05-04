import * as flowsActions from "../../../ducks/flows";
import { onKeyDown } from "../../../ducks/ui/keyboard";
import * as modalActions from "../../../ducks/ui/modal";
import { fetchApi, runCommand } from "../../../utils";
import { TFlow, TStore } from "../tutils";

jest.mock("../../../utils");

describe("onKeyDown", () => {
    const makeStore = () => {
        const store = TStore();
        store.dispatch(flowsActions.FLOWS_RECEIVE([]));
        store.dispatch(flowsActions.setFilter(""));
        for (let i = 1; i <= 12; i++) {
            store.dispatch(
                flowsActions.FLOWS_ADD({
                    ...TFlow(),
                    id: i + "",
                    websocket: undefined,
                    error: undefined,
                    intercepted: true,
                    modified: true,
                }),
            );
        }
        store.dispatch(flowsActions.select([store.getState().flows.list[0]]));
        return store;
    };

    const createKeyEvent = (key, ctrlKey = false) => {
        // @ts-expect-error not a real KeyboardEvent
        return onKeyDown({ key, ctrlKey, preventDefault: jest.fn() });
    };

    afterEach(() => {
        // @ts-expect-error mocking
        fetchApi.mockClear();
    });

    it("should handle cursor up/down", () => {
        const store = makeStore();
        // down
        store.dispatch(createKeyEvent("j"));
        expect(store.getState().flows.selected[0].id).toEqual("2");
        store.dispatch(createKeyEvent("ArrowDown"));
        expect(store.getState().flows.selected[0].id).toEqual("3");

        // up
        store.dispatch(createKeyEvent("k"));
        expect(store.getState().flows.selected[0].id).toEqual("2");
        store.dispatch(createKeyEvent("ArrowUp"));
        expect(store.getState().flows.selected[0].id).toEqual("1");
        store.dispatch(createKeyEvent("ArrowUp"));
        expect(store.getState().flows.selected[0].id).toEqual("1");
    });

    it("should handle scrolling", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("PageDown"));
        expect(store.getState().flows.selected[0].id).toEqual("11");
        store.dispatch(createKeyEvent("End"));
        expect(store.getState().flows.selected[0].id).toEqual("12");
        store.dispatch(createKeyEvent("PageUp"));
        expect(store.getState().flows.selected[0].id).toEqual("2");
        store.dispatch(createKeyEvent("Home"));
        expect(store.getState().flows.selected[0].id).toEqual("1");
    });

    it("should handle deselect", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("Escape"));
        expect(store.getState().flows.selected).toEqual([]);
    });

    it("should handle switch to left tab", () => {
        const store = makeStore();
        expect(store.getState().ui.flow.tab).toBe("request");
        store.dispatch(createKeyEvent("ArrowLeft"));
        expect(store.getState().ui.flow.tab).toBe("comment");
    });

    it("should handle switch to right tab", () => {
        const store = makeStore();
        expect(store.getState().ui.flow.tab).toBe("request");
        store.dispatch(createKeyEvent("Tab"));
        expect(store.getState().ui.flow.tab).toBe("response");
        store.dispatch(createKeyEvent("ArrowRight"));
        expect(store.getState().ui.flow.tab).toBe("connection");
    });

    it("should handle delete action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("d"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1", { method: "DELETE" });
    });

    it("should handle create action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("n"));
        expect(runCommand).toHaveBeenCalledWith(
            "view.flows.create",
            "get",
            "https://example.com/",
        );
    });

    it("should handle duplicate action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("D"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1/duplicate", {
            method: "POST",
        });
    });

    it("should handle resume action", async () => {
        const store = makeStore();
        await store.dispatch(createKeyEvent("a"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1/resume", {
            method: "POST",
        });
    });

    it("should handle resume all action", async () => {
        const store = makeStore();
        await store.dispatch(createKeyEvent("A"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/resume", {
            method: "POST",
        });
    });

    it("should handle replay action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("r"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1/replay", {
            method: "POST",
        });
    });

    it("should handle revert action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("v"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1/revert", {
            method: "POST",
        });
    });

    it("should handle kill action", () => {
        const store = makeStore();
        // kill all
        store.dispatch(createKeyEvent("X"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/kill", {
            method: "POST",
        });
        // kill
        store.dispatch(createKeyEvent("x"));
        expect(fetchApi).toHaveBeenCalledWith("/flows/1/kill", {
            method: "POST",
        });
    });

    it("should handle clear action", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("z"));
        expect(fetchApi).toHaveBeenCalledWith("/clear", { method: "POST" });
    });

    it("should stop on some action with no flow is selected", () => {
        const store = makeStore();
        store.dispatch(flowsActions.select([]));
        store.dispatch(createKeyEvent("ArrowLeft"));
        store.dispatch(createKeyEvent("Tab"));
        store.dispatch(createKeyEvent("ArrowRight"));
        store.dispatch(createKeyEvent("D"));
        expect(fetchApi).not.toHaveBeenCalled();
    });

    it("should do nothing when Ctrl and undefined key is pressed ", () => {
        const store = makeStore();
        store.dispatch(createKeyEvent("Backspace", true));
        store.dispatch(createKeyEvent(0));
        expect(fetchApi).not.toHaveBeenCalled();
    });

    it("should close modal", () => {
        const store = makeStore();
        store.dispatch(modalActions.setActiveModal("OptionModal"));
        expect(store.getState().ui.modal.activeModal).toEqual("OptionModal");
        store.dispatch(createKeyEvent("Escape"));
        expect(store.getState().ui.modal.activeModal).toEqual(undefined);
    });
});
