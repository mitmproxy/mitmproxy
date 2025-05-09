import reduceOptions, * as optionsActions from "../../ducks/options";
import { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "./tutils";
import { waitFor } from "@testing-library/dom";
import { OptionsStateWithMeta } from "../../ducks/options";

enableFetchMocks();

describe("option reducer", () => {
    it("should return initial state", () => {
        expect(reduceOptions(undefined, { type: "other" })).toEqual(
            optionsActions.defaultState,
        );
    });

    it("should handle receive action", () => {
        // @ts-expect-error mock
        const payload: OptionsStateWithMeta = { id: { value: "foo" } };
        const action = optionsActions.OPTIONS_RECEIVE(payload);
        expect(reduceOptions(undefined, action)).toEqual({ id: "foo" });
    });

    it("should handle update action", () => {
        // @ts-expect-error mock
        const payload: OptionsStateWithMeta = { id: { value: 1 } };
        const action = optionsActions.OPTIONS_UPDATE(payload);
        expect(reduceOptions(undefined, action)).toEqual({
            ...optionsActions.defaultState,
            id: 1,
        });
    });
});

test("sendUpdate", async () => {
    const store = TStore();

    fetchMock.mockResponseOnce("fooerror", { status: 404 });
    await store.dispatch(optionsActions.update("intercept", "~~~"));
    await waitFor(() =>
        expect(store.getState().ui.optionsEditor.intercept).toEqual({
            error: "fooerror",
            isUpdating: false,
            value: "~~~",
        }),
    );

    fetchMock.mockResponseOnce("", { status: 200 });
    await store.dispatch(optionsActions.update("intercept", "valid"));
    await waitFor(() =>
        expect(store.getState().ui.optionsEditor.intercept).toBeUndefined(),
    );
});

test("save", async () => {
    fetchMock.mockResponseOnce("");
    const store = TStore();
    await store.dispatch(optionsActions.save());
    expect(fetchMock).toBeCalled();
});

test("addInterceptFilter", async () => {
    fetchMock.mockClear();
    fetchMock.mockResponses("", "");
    const store = TStore();
    await store.dispatch(optionsActions.addInterceptFilter("~u foo"));
    expect(fetchMock.mock.calls[0][1]?.body).toEqual('{"intercept":"~u foo"}');

    const payload: Partial<OptionsStateWithMeta> = {
        intercept: {
            value: "~u foo",
            default: "",
            help: "Intercept filter",
            type: "str",
        },
    };
    store.dispatch(optionsActions.OPTIONS_UPDATE(payload));

    await store.dispatch(optionsActions.addInterceptFilter("~u foo"));
    expect(fetchMock.mock.calls).toHaveLength(1);

    await store.dispatch(optionsActions.addInterceptFilter("~u bar"));
    expect(fetchMock.mock.calls[1][1]?.body).toEqual(
        '{"intercept":"~u foo | ~u bar"}',
    );
});
