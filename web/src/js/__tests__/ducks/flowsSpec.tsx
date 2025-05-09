import reduceFlows, * as flowActions from "../../ducks/flows";
import { fetchApi } from "../../utils";
import { TFlow, TStore, TTCPFlow } from "./tutils";
import FlowColumns from "../../components/FlowTable/FlowColumns";

jest.mock("../../utils");

describe("flow reducer", () => {
    let s;
    for (const i of ["0", "1", "2", "3", "4"]) {
        s = reduceFlows(s, flowActions.FLOWS_ADD({ ...TFlow(), id: i }));
    }
    const state = s;
    const [_f0, f1, f2, f3, f4] = state.list;
    const alreadySelected = {
        ...state,
        selected: [f1],
        selectedIndex: { "1": 0 },
    };

    describe("selections", () => {
        it("should be possible to select a single flow", () => {
            expect(reduceFlows(state, flowActions.select([f1]))).toEqual({
                ...state,
                selected: [f1],
                selectedIndex: { "1": 0 },
            });
        });

        it("should be possible to select multiple flows", () => {
            expect(reduceFlows(state, flowActions.select([f1, f2]))).toEqual({
                ...state,
                selected: [f1, f2],
                selectedIndex: { "1": 0, "2": 1 },
            });
        });

        it("should be possible to deselect a flow", () => {
            expect(
                reduceFlows(alreadySelected, flowActions.select([])),
            ).toEqual({
                ...state,
                selected: [],
                selectedIndex: {},
            });
        });

        it("should be possible to select relative", () => {
            // haven't selected any flow
            expect(flowActions.selectRelative(state, 1)).toEqual(
                flowActions.select([f4]),
            );

            // already selected some flows
            expect(flowActions.selectRelative(alreadySelected, 1)).toEqual(
                flowActions.select([f2]),
            );
        });

        it("should be possible to toggle selections", () => {
            const store = TStore();
            const [tflow0, tflow1] = store.getState().flows.list;
            store.dispatch(flowActions.selectToggle(tflow0));
            expect(store.getState().flows.selected).toEqual([tflow1, tflow0]);
            expect(store.getState().flows.selectedIndex).toEqual({
                [tflow1.id]: 0,
                [tflow0.id]: 1,
            });

            store.dispatch(flowActions.selectToggle(tflow1));
            expect(store.getState().flows.selected).toEqual([tflow0]);
            expect(store.getState().flows.selectedIndex).toEqual({
                [tflow0.id]: 0,
            });
        });

        it("should be possible to do range selections", () => {
            const store = TStore();
            const [_tflow0, tflow1, tflow2, tflow3] =
                store.getState().flows.list;
            store.dispatch(flowActions.select([tflow2]));

            store.dispatch(flowActions.selectRange(tflow1));
            expect(store.getState().flows.selected).toEqual([tflow1, tflow2]);

            store.dispatch(flowActions.selectRange(tflow3));
            expect(store.getState().flows.selected).toEqual([tflow3, tflow2]);
        });

        it("should update state.selected on remove", () => {
            let next;
            next = reduceFlows(alreadySelected, flowActions.FLOWS_REMOVE("1"));
            expect(next.selected).toEqual([f2]);

            //last row
            next = reduceFlows(
                { ...state, selected: [f4], selectedIndex: { "4": 0 } },
                flowActions.FLOWS_REMOVE("4"),
            );
            expect(next.selected).toEqual([f3]);

            //multiple selection
            next = reduceFlows(
                {
                    ...state,
                    selected: [f2, f3],
                    selectedIndex: { "2": 0, "3": 1 },
                },
                flowActions.FLOWS_REMOVE("3"),
            );
            expect(next.selected).toEqual([f2]);
        });

        it("should keep only selected flows that exist in byId during RECEIVE", () => {
            const store = TStore();
            const originalState = store.getState().flows;

            // Simulate selected flows: one valid, one missing from byId
            const stillExists = originalState.list[1];
            const removedFlow = { ...stillExists, id: "missing-id" };

            const modifiedState = {
                ...originalState,
                selected: [stillExists, removedFlow],
                selectedIndex: {
                    [stillExists.id]: 0,
                    [removedFlow.id]: 1,
                },
                byId: {
                    [stillExists.id]: stillExists,
                },
            };

            const next = reduceFlows(
                modifiedState,
                flowActions.FLOWS_RECEIVE([stillExists]),
            );

            expect(next.selected).toEqual([stillExists]);
            expect(next.selectedIndex).toEqual({ [stillExists.id]: 0 });
        });

        it("should not update the flow in state.selected if the id doesn't exist in selectedIndex", () => {
            const store = TStore();
            const originalSelected = store.getState().flows.selected;

            const unrelatedFlow = {
                ...originalSelected[0],
                id: "nonexistent-id",
            };

            const next = reduceFlows(
                store.getState().flows,
                flowActions.FLOWS_UPDATE(unrelatedFlow),
            );
            expect(next.selected).toEqual(originalSelected);
        });

        it("should update the flow in state.selected if the id exists in selectedIndex", () => {
            const store = TStore();
            const [tflow1] = store.getState().flows.selected;

            const updatedFlow = {
                ...tflow1,
                comment: "I'm a modified comment!",
            };

            const next = reduceFlows(
                store.getState().flows,
                flowActions.FLOWS_UPDATE(updatedFlow),
            );
            const updatedSelected = next.selected;
            expect(updatedSelected[0]).toBe(updatedFlow);
        });

        it("should not update state.selected on remove if action.data is undefined", () => {
            const next = reduceFlows(
                state,
                flowActions.FLOWS_REMOVE("unknown"),
            );
            expect(next).toEqual(state);
        });

        it("should clear selected when the flow id doesn't exist in viewIndex during REMOVE", () => {
            const store = TStore();
            const originalState = store.getState().flows;

            const selectedFlow = originalState.list[0];

            const modifiedState = {
                ...originalState,
                selected: [selectedFlow],
                selectedIndex: {
                    [selectedFlow.id]: 0,
                },
                viewIndex: {},
            };

            const next = reduceFlows(
                modifiedState,
                flowActions.FLOWS_REMOVE(selectedFlow.id),
            );

            expect(next.selected).toEqual([]);
            expect(next.selectedIndex).toEqual({});
        });
    });

    it("should be possible to set filter", () => {
        const filt = "~u 123";
        expect(
            reduceFlows(undefined, flowActions.setFilter(filt)).filter,
        ).toEqual(filt);
    });

    it("should be possible to set highlight", () => {
        const key = "foo";
        expect(
            reduceFlows(undefined, flowActions.setHighlight(key)).highlight,
        ).toEqual(key);
    });

    it("should be possible to set sort", () => {
        const sort = { column: "tls" as const, desc: true };
        expect(reduceFlows(undefined, flowActions.setSort(sort)).sort).toEqual(
            sort,
        );
    });
});

describe("flows actions", () => {
    const store = TStore();
    const tflow = TFlow();
    tflow.intercepted = true;
    tflow.modified = true;
    // @ts-expect-error TFlow is Required<> for other tests.
    tflow.websocket = undefined;
    const ttcpflow = TTCPFlow();

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("should handle resume action", () => {
        store.dispatch(flowActions.resume([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/resume",
            { method: "POST" },
        );
    });

    it("should handle resumeAll action", () => {
        store.dispatch(flowActions.resumeAll());
        expect(fetchApi).toBeCalledWith("/flows/resume", { method: "POST" });
    });

    it("should handle kill action", () => {
        store.dispatch(flowActions.kill([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/kill",
            { method: "POST" },
        );
    });

    it("should handle killAll action", () => {
        store.dispatch(flowActions.killAll());
        expect(fetchApi).toBeCalledWith("/flows/kill", { method: "POST" });
    });

    it("should handle remove action", () => {
        store.dispatch(flowActions.remove([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29",
            { method: "DELETE" },
        );
    });

    it("should handle remove action with multiple flows", async () => {
        await store.dispatch(flowActions.remove([tflow, ttcpflow]));

        expect(fetchApi).toHaveBeenCalledTimes(2);
        expect(fetchApi).toHaveBeenCalledWith(`/flows/${tflow.id}`, {
            method: "DELETE",
        });
        expect(fetchApi).toHaveBeenCalledWith(`/flows/${ttcpflow.id}`, {
            method: "DELETE",
        });
    });

    it("should handle duplicate action", () => {
        store.dispatch(flowActions.duplicate([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/duplicate",
            { method: "POST" },
        );
    });

    it("should handle replay action", () => {
        store.dispatch(flowActions.replay([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/replay",
            { method: "POST" },
        );
    });

    it("should handle revert action", () => {
        store.dispatch(flowActions.revert([tflow]));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/revert",
            { method: "POST" },
        );
    });

    it("should handle mark action", async () => {
        store.dispatch(flowActions.mark([tflow, ttcpflow], ":red_circle:"));
        expect(fetchApi.put).toHaveBeenCalledWith(`/flows/${tflow.id}`, {
            marked: ":red_circle:",
        });
        expect(fetchApi.put).toHaveBeenCalledWith(`/flows/${ttcpflow.id}`, {
            marked: ":red_circle:",
        });
    });

    it("should handle update action", () => {
        store.dispatch(flowActions.update(tflow, "foo"));
        expect(fetchApi.put).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29",
            "foo",
        );
    });

    it("should handle uploadContent action", () => {
        const body = new FormData();
        const file = new window.Blob(["foo"], { type: "plain/text" });
        body.append("file", file);
        store.dispatch(flowActions.uploadContent(tflow, "foo", "foo"));
        // window.Blob's lastModified is always the current time,
        // which causes flaky tests on comparison.
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/foo/content.data",
            {
                method: "POST",
                body: expect.anything(),
            },
        );
    });

    it("should handle clear action", () => {
        store.dispatch(flowActions.clear());
        expect(fetchApi).toBeCalledWith("/clear", { method: "POST" });
    });

    it("should handle upload action", () => {
        const body = new FormData();
        body.append("file", "foo");
        store.dispatch(flowActions.upload("foo"));
        expect(fetchApi).toBeCalledWith("/flows/dump", {
            method: "POST",
            body,
        });
    });
});

test("makeSort", () => {
    const a = TFlow();
    const b = TFlow();
    a.request.scheme = "https";
    a.request.method = "POST";
    a.request.path = "/foo";
    a.response.contentLength = 42;
    a.response.status_code = 418;

    Object.keys(FlowColumns).forEach((column, i) => {
        // @ts-expect-error jest is funky about type annotations here.
        const sort = flowActions.makeSort({ column, desc: i % 2 == 0 });
        expect(sort(a, b)).toBeDefined();
    });
});
