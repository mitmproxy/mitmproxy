import { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "../ducks/tutils";
import StaticBackend from "../../backends/static";
import { waitFor } from "../test-utils";

enableFetchMocks();

test("static backend", async () => {
    fetchMock.mockOnceIf("./flows", "[]");
    fetchMock.mockOnceIf("./options", "{}");
    const store = TStore();
    new StaticBackend(store);
    await waitFor(() => {
        expect(store.getState().flows.list).toEqual([]);
        expect(store.getState().options).toEqual({});
    });
});
