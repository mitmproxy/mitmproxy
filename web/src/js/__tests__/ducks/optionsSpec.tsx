import reduceOptions, * as optionsActions from "../../ducks/options";
import { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "./tutils";
import { waitFor } from "@testing-library/dom";

enableFetchMocks();

describe("option reducer", () => {
    it("should return initial state", () => {
        expect(reduceOptions(undefined, { type: "other" })).toEqual(
            optionsActions.defaultState,
        );
    });

    it("should handle receive action", () => {
        const action = {
            type: optionsActions.RECEIVE,
            data: { id: { value: "foo" } },
        };
        expect(reduceOptions(undefined, action)).toEqual({ id: "foo" });
    });

    it("should handle update action", () => {
        const action = {
            type: optionsActions.UPDATE,
            data: { id: { value: 1 } },
        };
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

    store.dispatch({
        type: optionsActions.UPDATE,
        data: { intercept: { value: "~u foo" } },
    });

    await store.dispatch(optionsActions.addInterceptFilter("~u foo"));
    expect(fetchMock.mock.calls).toHaveLength(1);

    await store.dispatch(optionsActions.addInterceptFilter("~u bar"));
    expect(fetchMock.mock.calls[1][1]?.body).toEqual(
        '{"intercept":"~u foo | ~u bar"}',
    );
});
