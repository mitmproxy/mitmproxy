import reduceFlows, * as flowActions from "../../ducks/flows";
import { reduce } from "../../ducks/utils/store";
import { fetchApi } from "../../utils";
import { TFlow, TStore } from "./tutils";
import FlowColumns from "../../components/FlowTable/FlowColumns";

jest.mock("../../utils");

describe("flow reducer", () => {
    let s;
    for (const i of ["1", "2", "3", "4"]) {
        s = reduceFlows(s, {
            type: flowActions.ADD,
            data: { id: i },
            cmd: "add",
        });
    }
    const state = s;

    it("should return initial state", () => {
        expect(reduceFlows(undefined, {})).toEqual({
            highlight: undefined,
            filter: undefined,
            sort: { column: undefined, desc: false },
            selected: [],
            ...reduce(undefined, {}),
        });
    });

    describe("selections", () => {
        it("should be possible to select a single flow", () => {
            expect(reduceFlows(state, flowActions.select("2"))).toEqual({
                ...state,
                selected: ["2"],
            });
        });

        it("should be possible to deselect a flow", () => {
            expect(
                reduceFlows(
                    { ...state, selected: ["1"] },
                    flowActions.select(),
                ),
            ).toEqual({
                ...state,
                selected: [],
            });
        });

        it("should be possible to select relative", () => {
            // haven't selected any flow
            expect(flowActions.selectRelative(state, 1)).toEqual(
                flowActions.select("4"),
            );

            // already selected some flows
            expect(
                flowActions.selectRelative({ ...state, selected: [2] }, 1),
            ).toEqual(flowActions.select("3"));
        });

        it("should update state.selected on remove", () => {
            let next;
            next = reduceFlows(
                { ...state, selected: ["2"] },
                {
                    type: flowActions.REMOVE,
                    data: "2",
                    cmd: "remove",
                },
            );
            expect(next.selected).toEqual(["3"]);

            //last row
            next = reduceFlows(
                { ...state, selected: ["4"] },
                {
                    type: flowActions.REMOVE,
                    data: "4",
                    cmd: "remove",
                },
            );
            expect(next.selected).toEqual(["3"]);

            //multiple selection
            next = reduceFlows(
                { ...state, selected: ["2", "3", "4"] },
                {
                    type: flowActions.REMOVE,
                    data: "3",
                    cmd: "remove",
                },
            );
            expect(next.selected).toEqual(["2", "4"]);
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
        const sort = { column: "tls", desc: true };
        expect(
            reduceFlows(undefined, flowActions.setSort(sort.column, sort.desc))
                .sort,
        ).toEqual(sort);
    });
});

describe("flows actions", () => {
    const store = TStore();
    const tflow = TFlow();

    it("should handle resume action", () => {
        store.dispatch(flowActions.resume(tflow));
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
        store.dispatch(flowActions.kill(tflow));
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
        store.dispatch(flowActions.remove(tflow));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29",
            { method: "DELETE" },
        );
    });

    it("should handle duplicate action", () => {
        store.dispatch(flowActions.duplicate(tflow));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/duplicate",
            { method: "POST" },
        );
    });

    it("should handle replay action", () => {
        store.dispatch(flowActions.replay(tflow));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/replay",
            { method: "POST" },
        );
    });

    it("should handle revert action", () => {
        store.dispatch(flowActions.revert(tflow));
        expect(fetchApi).toBeCalledWith(
            "/flows/d91165be-ca1f-4612-88a9-c0f8696f3e29/revert",
            { method: "POST" },
        );
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
