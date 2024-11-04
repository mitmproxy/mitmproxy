import fetchMock, { enableFetchMocks } from "jest-fetch-mock";
import { TStore } from "../tutils";
import { isActiveMode, updateModes } from "../../../ducks/modes/utils";

enableFetchMocks();

describe("updateMode action creator", () => {
    beforeEach(() => {
        fetchMock.resetMocks();
    });

    it("should call updateMode method with a successful api call", async () => {
        const store = TStore();
        fetchMock.mockResponseOnce(JSON.stringify({ success: true }));

        await store.dispatch(() => updateModes(null, store));

        const expectedUrl = "./options";
        const expectedBody = JSON.stringify({ mode: ["regular"] });

        const actualCall = fetchMock.mock.calls[0];
        const actualUrl = actualCall[0];
        const actualBody = actualCall[1]?.body;

        expect(actualUrl).toEqual(expectedUrl);
        expect(actualBody).toEqual(expectedBody);
    });

    it("fetch HTTP status != 200 throws", async () => {
        const store = TStore();
        fetchMock.mockResponseOnce("invalid query", { status: 400 });
        await expect(
            store.dispatch(() => updateModes(null, store)),
        ).rejects.toThrow("invalid query");
    });

    it("fetch error throws", async () => {
        const store = TStore();
        fetchMock.mockRejectOnce(new Error("network error"));
        await expect(
            store.dispatch(() => updateModes(null, store)),
        ).rejects.toThrow("network error");
    });
});

describe("isActiveMode", () => {
    it("should work", () => {
        expect(isActiveMode({ active: false })).toBe(false);
        expect(isActiveMode({ active: true })).toBe(true);
        expect(isActiveMode({ active: true, error: "failed" })).toBe(false);
        expect(isActiveMode({ active: false, error: "failed" })).toBe(false);
    });
});
