import reduceFlows, * as flowActions from "../../../ducks/flows";
import { defaultState } from "../../../ducks/flows";
import { testState, TFlow, TStore } from "../tutils";
import FlowColumns from "../../../components/FlowTable/FlowColumns";
import { FilterName } from "../../../ducks/ui/filter";

describe("flow reducer", () => {
    let s;
    for (const i of ["0", "1", "2", "3", "4"]) {
        s = reduceFlows(
            s,
            flowActions.FLOWS_ADD({
                flow: { ...TFlow(), id: i },
                matching_filters: {},
            }),
        );
    }
    const state = reduceFlows(
        undefined,
        flowActions.FLOWS_RECEIVE([
            { ...TFlow(), id: "0" },
            { ...TFlow(), id: "1" },
            { ...TFlow(), id: "2" },
            { ...TFlow(), id: "3", comment: "foo" },
            { ...TFlow(), id: "4" },
        ]),
    );
    const [f0, f1, f2, f3, f4] = state.list;

    describe("flow updates during fetch (WebSocket/HTTP race)", () => {
        it("should handle flows/add for existing flows", () => {
            expect(
                reduceFlows(
                    state,
                    flowActions.FLOWS_ADD({ flow: f1, matching_filters: {} }),
                ),
            ).toEqual(state);
        });
        it("should handle flows/update for unknown flows", () => {
            expect(
                reduceFlows(
                    state,
                    flowActions.FLOWS_UPDATE({
                        flow: { ...TFlow(), id: "5" },
                        matching_filters: {},
                    }),
                ).byId.get("5"),
            ).toBeTruthy();
        });
        it("should handle flows/remove for unknown flow", () => {
            expect(
                reduceFlows(state, flowActions.FLOWS_REMOVE("unknown-flow-id")),
            ).toEqual(state);
        });
        it("should handle filter update for unknown flows", () => {
            expect(
                reduceFlows(
                    state,
                    flowActions.FLOWS_FILTER_UPDATE({
                        name: FilterName.Search,
                        matching_flow_ids: ["unknown-flow-id", "4"],
                    }),
                ).view,
            ).toEqual([f4]);
        });
    });

    describe("selections", () => {
        const alreadySelected = reduceFlows(state, flowActions.select([f1]));
        expect(alreadySelected).not.toEqual(state);

        it("should be possible to select a single flow", () => {
            expect(reduceFlows(state, flowActions.select([f1]))).toEqual({
                ...state,
                selected: [f1],
                selectedIds: new Set(["1"]),
            });
        });

        it("should be possible to select multiple flows", () => {
            expect(reduceFlows(state, flowActions.select([f1, f2]))).toEqual({
                ...state,
                selected: [f1, f2],
                selectedIds: new Set(["1", "2"]),
            });
        });

        it("should be possible to deselect a flow", () => {
            expect(
                reduceFlows(alreadySelected, flowActions.select([])),
            ).toEqual(state);
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

            // empty
            expect(flowActions.selectRelative(defaultState, 1)).toEqual(
                flowActions.select([]),
            );
        });

        it("should be possible to toggle selections", () => {
            const store = TStore();
            const [tflow0, tflow1] = store.getState().flows.list;
            store.dispatch(flowActions.selectToggle(tflow0));
            expect(store.getState().flows.selected).toEqual([tflow1, tflow0]);

            store.dispatch(flowActions.selectToggle(tflow1));
            expect(store.getState().flows.selected).toEqual([tflow0]);
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

            // selection is not in view?
            store.dispatch(
                flowActions.FLOWS_FILTER_UPDATE({
                    name: FilterName.Search,
                    matching_flow_ids: [tflow1.id],
                }),
            );
            store.dispatch(flowActions.selectRange(tflow1));
            expect(store.getState().flows.selected).toEqual([tflow1]);
        });

        it("should select next row on remove", () => {
            const s = reduceFlows(
                alreadySelected,
                flowActions.FLOWS_REMOVE("1"),
            );
            expect(s.selected).toEqual([f2]);
        });

        it("should select next row on remove (last row)", () => {
            let s = reduceFlows(state, flowActions.select([f4]));
            s = reduceFlows(s, flowActions.FLOWS_REMOVE("4"));
            expect(s.selected).toEqual([f3]);
        });

        it("should remove from multi-selection", () => {
            s = reduceFlows(state, flowActions.select([f2, f3]));
            s = reduceFlows(s, flowActions.FLOWS_REMOVE("3"));
            expect(s.selected).toEqual([f2]);
        });

        it("should clear selection when last flow is removed", () => {
            s = reduceFlows(defaultState, flowActions.FLOWS_RECEIVE([f1]));
            s = reduceFlows(s, flowActions.select([f1]));
            s = reduceFlows(s, flowActions.FLOWS_REMOVE("1"));
            expect(s.selected).toEqual([]);
        });

        it("should keep only selected flows that exist in byId during RECEIVE", () => {
            let state = testState.flows,
                [f0, f1, ..._] = state.list;
            state = reduceFlows(state, flowActions.select([f0, f1]));
            expect(state.selected).toEqual([f0, f1]);

            state = reduceFlows(state, flowActions.FLOWS_RECEIVE([f0]));

            expect(state.selected).toEqual([f0]);
            expect(state.selectedIds).toEqual(new Set([f0.id]));
        });

        it("should update the flow in state.selected", () => {
            const f1Updated = {
                ...f1,
                comment: "I'm a modified comment!",
            };

            let s = reduceFlows(state, flowActions.select([f1, f2]));
            s = reduceFlows(
                s,
                flowActions.FLOWS_UPDATE({
                    flow: f1Updated,
                    matching_filters: {},
                }),
            );
            expect(s.selected).toEqual([f1Updated, f2]);
        });
    });

    describe("highlighting", () => {
        const alreadyHighlighted = reduceFlows(
            state,
            flowActions.FLOWS_UPDATE({
                flow: f1,
                matching_filters: {
                    [FilterName.Highlight]: true,
                },
            }),
        );
        expect(alreadyHighlighted).not.toEqual(state);

        it("should add flows that are highlighted", () => {
            let s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Highlight]: true,
                    },
                }),
            );
            expect(s.highlightedIds).toContain("1");
            s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Highlight]: false,
                    },
                }),
            );
            expect(s.highlightedIds).not.toContain("1");
            s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {},
                }),
            );
            expect(s.highlightedIds).not.toContain("1");
        });
        it("should update highlight state", () => {
            let s = reduceFlows(
                state,
                flowActions.FLOWS_UPDATE({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Highlight]: true,
                    },
                }),
            );
            expect(s.highlightedIds).toContain("1");
            s = reduceFlows(
                state,
                flowActions.FLOWS_UPDATE({
                    flow: f1,
                    matching_filters: {},
                }),
            );
            expect(s.highlightedIds).not.toContain("1");
        });
        it("should discard removed flows from highlight", () => {
            let s = reduceFlows(
                alreadyHighlighted,
                flowActions.FLOWS_REMOVE("1"),
            );
            expect(s.highlightedIds).not.toContain("1");
        });
        it("should update highlight filters", () => {
            let s = reduceFlows(
                alreadyHighlighted,
                flowActions.FLOWS_FILTER_UPDATE({
                    name: FilterName.Highlight,
                    matching_flow_ids: ["2", "3"],
                }),
            );
            expect(s.highlightedIds).toEqual(new Set(["2", "3"]));
        });
    });

    describe("filtering", () => {
        it("should add flows that are filtered", () => {
            let s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Search]: true,
                    },
                }),
            );
            expect(s.view).toContain(f1);
            s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Search]: false,
                    },
                }),
            );
            expect(s.view).not.toContain(f1);
            s = reduceFlows(
                undefined,
                flowActions.FLOWS_ADD({
                    flow: f1,
                    matching_filters: {},
                }),
            );
            expect(s.view).toContain(f1);
        });
        it("should update flows that are filtered", () => {
            let s = reduceFlows(
                state,
                flowActions.FLOWS_UPDATE({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Search]: true,
                    },
                }),
            );
            expect(s.view).toContain(f1);
            s = reduceFlows(
                s,
                flowActions.FLOWS_UPDATE({
                    flow: f1,
                    matching_filters: {
                        [FilterName.Search]: false,
                    },
                }),
            );
            expect(s.view).not.toContain(f1);
            s = reduceFlows(
                s,
                flowActions.FLOWS_UPDATE({
                    flow: f1,
                    matching_filters: {},
                }),
            );
            expect(s.view).toContain(f1);
        });
        it("should update search filters", () => {
            let s = reduceFlows(
                state,
                flowActions.FLOWS_FILTER_UPDATE({
                    name: FilterName.Search,
                    matching_flow_ids: ["2", "3"],
                }),
            );
            expect(s.view).toEqual([f2, f3]);
        });
    });

    describe("sorting", () => {
        it("should sort", () => {
            const sort = { column: "comment" as const, desc: true };
            expect(reduceFlows(state, flowActions.setSort(sort))).toEqual({
                ...reduceFlows(
                    undefined,
                    flowActions.FLOWS_RECEIVE([f3, f0, f1, f2, f4]),
                ),
                list: state.list,
                _listIndex: state._listIndex,
                sort,
            });
        });
        it("should restore original order if column is undefined", () => {
            let s = reduceFlows(
                state,
                flowActions.setSort({ column: "comment", desc: true }),
            );
            expect(s.view).not.toEqual(state.view);
            s = reduceFlows(
                s,
                flowActions.setSort({ column: undefined, desc: false }),
            );
            expect(s.view).toEqual(state.view);
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
    a.response.status_code = 101;

    Object.keys(FlowColumns).forEach((column, i) => {
        // @ts-expect-error jest is funky about type annotations here.
        const sort = flowActions.makeSort({ column, desc: i % 2 == 0 });
        expect(sort(a, b)).toBeDefined();
    });
});
