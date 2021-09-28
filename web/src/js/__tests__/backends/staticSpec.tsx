import {enableFetchMocks} from "jest-fetch-mock";
import {TStore} from "../ducks/tutils";
import StaticBackend from "../../backends/static";
import {waitFor} from "../test-utils";

enableFetchMocks();

test("static backend", async () => {
    fetchMock.mockOnceIf("./flows", "[]");
    fetchMock.mockOnceIf("./options", "{}");
    const store = TStore();
    const backend = new StaticBackend(store);
    await waitFor(() => expect(store.getActions()).toEqual([
        {type: "FLOWS_RECEIVE", cmd: "receive", data: [], resource: "flows"},
        {type: "OPTIONS_RECEIVE", cmd: "receive", data: {}, resource: "options"}
    ]))
});
