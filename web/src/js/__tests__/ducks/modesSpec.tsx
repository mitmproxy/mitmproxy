import { updateMode } from "../../ducks/modes";
import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "./tutils";
import { fetchApi } from "../../utils";

jest.mock("../../utils", () => ({
    fetchApi: {
        put: jest.fn(), // You might need to mock this function properly
    },
}));

describe("updateMode action creator", () => {
    beforeEach(() => {
        enableFetchMocks();
        fetchMock.mockClear();
    });

    it("should call updateMode method with a successful api call", async () => {
        const store = TStore();

        (fetchApi.put as jest.Mock).mockResolvedValueOnce({ status: 200 });

        await store.dispatch(updateMode());

        expect(store.getState().modes).toEqual({
            regular: {
                active: true,
                name: "regular",
            },
            local: {
                active: false,
                name: "local",
                applications: ""
            },
        });
    });
});
